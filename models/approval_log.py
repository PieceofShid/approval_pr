from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.request'

    approval_log = fields.One2many('ics.approval.pr.log', 'request_id', string="Approval Log")
    
class ApprovalLog(models.Model):
    _name = 'ics.approval.pr.log'

    request_id  = fields.Many2one('purchase.request', string="Purchase Request", readonly=True, required=True)
    approver_id = fields.Many2one('res.users', string="Approver")
    from_action = fields.Char(string="From")
    to_action   = fields.Char(string="To")
    datetime    = fields.Datetime(string="Date & Time", default=lambda self: fields.Datetime.now())