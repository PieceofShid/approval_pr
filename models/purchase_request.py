from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    company_unit_id = fields.Many2one('ics.company.unit', string="Company Unit")
    final_approve_date = fields.Date(string='Date approve final', readonly=True, copy=False)
    checker_id = fields.Many2one('res.user', string="Checker", copy=False)
    lead_time_date = fields.Date(string='Date lead time', readonly=True, copy=False)
    state = fields.Selection(selection_add=[
        ('pending_release', 'Pending Release'),
        ('waiting_release', 'Waiting Release'),
        ('waiting_complete', 'Waiting Complete'),
        ("approved",), ], ondelete={'pending_release': 'set default', 'waiting_release': 'set default', 'waiting_complete': 'set default'})
    budget_allocation = fields.Selection(selection=[
        ('AVP', 'AVP'),
        ('Teri', 'Teri')
    ])
    
    def _get_approval_config_status(self):
        for purchase in self:
            approval = self.env['ics.approval.pr.config'].search([], limit=1)
            purchase.is_approval_active = approval.active
    
    is_approval_active = fields.Boolean(string="Is Approval Active", compute=_get_approval_config_status)

    def _show_rejected_button(self):
        for purchase in self:
            company_unit_request = purchase.requested_by.company_unit_id
            company_unit_users   = self.env.user.company_unit_id
            if company_unit_request.id == company_unit_users.id and purchase.state in ('pending_release', 'waiting_release', 'waiting_complete'):
                purchase.is_show_rejected_button = True
            else:
                purchase.is_show_rejected_button = False
                
    is_show_rejected_button = fields.Boolean(string="Show Reject Buttom", compute=_show_rejected_button)

    @api.onchange('requested_by')
    def _get_default_company_uni(self):
        for request in self:
            request = request.with_company(request.company_id)
            request.write({
                'company_unit_id': request.requested_by.company_unit_id
            })

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("to_approve", "pending_release", "waiting_release", "waiting_complete", "approved", "rejected", "done"):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_to_approve(self):
        approval = self.env['ics.approval.pr.config'].search([], limit=1)

        if approval.active == False:
            self.to_approve_allowed_check()
            return self.write({"state": "to_approve"})
        
        return True
    
    def button_approved(self):
        today = datetime.today()
        lead  = today + timedelta(days=21)
        return self.write({"state": "approved",
                           "assigned_to": self.env.uid,
                           "final_approve_date": today,
                           "lead_time_date": lead})
    
    def _get_approval_log(self):
        logs = self.approval_log.search([
            ('from_action', '!=', 'Draft'),
            ('to_action', '!=', 'Complete'),
            ('request_id', '=', self.id)])
        approver = []

        for log in logs:
            logging = self.env['ics.approval.pr.log'].search([
                ('to_action', '=', log.to_action),
                ('request_id', '=', log.request_id.id)],
                order='datetime DESC', limit=1)

            approver.append({
                'name': logging.approver_id.name,
                'signature': logging.approver_id.signature_image
            })

        return approver
    
    def _get_approval_complete(self):
        logs = self.approval_log.search([
            ('to_action', '=', 'Complete'),
            ('request_id', '=', self.id)], order='datetime DESC', limit=1)
        
        return {
            'name': logs.approver_id.name,
            'signature': logs.approver_id.signature_image
        }

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    budget_allocation = fields.Selection(selection=[
        ('AVP', 'AVP'),
        ('Teri', 'Teri')
    ])

class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    lead_time_date = fields.Date(string="Lead Time", compute="_get_parent_lead_time")
    price_unit = fields.Monetary(string="Price Unit", default=0.0)

    def _get_parent_lead_time(self):
        request = self.request_id

        self.lead_time_date = request.lead_time_date

    @api.onchange("price_unit", "product_qty")
    def _get_estimated_cost(self):
        for request in self:
            request.estimated_cost = request.price_unit * request.product_qty

class PurchaseOrderLines(models.Model):
    _inherit = 'purchase.order.line'

    specifications = fields.Char(string="Specifications")

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        request_ids = self.env.context.get("active_ids", False)

        request = self.env['purchase.request'].browse(request_ids)

        if not self.supplier_id:
            raise UserError(_("Enter a supplier."))
        supplier = self.supplier_id
        data = {
            "origin": origin,
            "partner_id": self.supplier_id.id,
            "payment_term_id": self.supplier_id.property_supplier_payment_term_id.id,
            "fiscal_position_id": supplier.property_account_position_id
            and supplier.property_account_position_id.id
            or False,
            "picking_type_id": picking_type.id,
            "company_id": company.id,
            "group_id": group_id.id,
            "budget_allocation": request.budget_allocation
        }
        return data

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        if not item.product_id:
            raise UserError(_("Please select a product for all lines"))
        product = item.product_id

        # Keep the standard product UOM for purchase order so we should
        # convert the product quantity to this UOM
        qty = item.product_uom_id._compute_quantity(
            item.product_qty, product.uom_po_id or product.uom_id
        )
        # Suggest the supplier min qty as it's done in Odoo core
        min_qty = item.line_id._get_supplier_min_qty(product, po.partner_id)
        qty = max(qty, min_qty)
        date_required = item.line_id.date_required
        return {
            "order_id": po.id,
            "product_id": product.id,
            "product_uom": product.uom_po_id.id or product.uom_id.id,
            "price_unit": 0.0,
            "product_qty": qty,
            "specifications": item.line_id.specifications,
            "analytic_distribution": item.line_id.analytic_distribution,
            "purchase_request_lines": [(4, item.line_id.id)],
            "lead_time": item.line_id.lead_time_date,
            "date_planned": datetime(
                date_required.year, date_required.month, date_required.day
            ),
            "move_dest_ids": [(4, x.id) for x in item.line_id.move_dest_ids],
        }