from odoo import models, fields, api
from datetime import datetime, timedelta

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    company_unit_id = fields.Many2one('ics.company.unit', string="Company Unit")
    final_approve_date = fields.Date(string='Date approve final', readonly=True)
    checker_id = fields.Many2one('res.user', string="Checker")
    lead_time_date = fields.Date(string='Date lead time', readonly=True)
    state = fields.Selection(selection_add=[
        ('pending_release', 'Pending Release'),
        ('waiting_release', 'Waiting Release'),
        ('waiting_complete', 'Waiting Complete'),
        ("approved",), ], ondelete={'pending_release': 'set default', 'waiting_release': 'set default', 'waiting_complete': 'set default'})
    
    def _get_approval_config_status(self):
        for purchase in self:
            approval = self.env['ics.approval.pr.config'].search([], limit=1)
            purchase.is_approval_active = approval.active
    
    is_approval_active = fields.Boolean(string="Is Approval Active", compute=_get_approval_config_status)

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