from odoo import models, fields, api

class ApprovalConfig(models.Model):
    _name = 'ics.approval.pr.config'
    _description = 'Configuration approval for purchase request'

    name = fields.Char(string='Reference', required=True, default="Approval Purchase Request")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    rule_id = fields.One2many('ics.approval.pr.rule', 'approval_config_id', string='Approval PR Rule')
    active = fields.Boolean(string="Active", default=False)

    def _get_groups_purchase_request(self):
        group_categ_id = self.env.ref('purchase_request.module_category_purchase_request')

        self.group_category = group_categ_id.id

    group_category = fields.Many2one('ir.module.category', string='Group Domain', compute=_get_groups_purchase_request)

class ApprovalRule(models.Model):
    _name = 'ics.approval.pr.rule'
    _description = 'Rule approval for purchase request based on users'

    approval_config_id = fields.Many2one('ics.approval.pr.config', string="Config Reference", required=True, ondelete="cascade", index=True, copy=False)
    name = fields.Char(string='Action Reference', required=True)
    state = fields.Selection(string='State', required=True, selection=[
        ('draft', 'Draft'),
        ('pending_release', 'Pending Release'),
        ('waiting_release', 'Waiting Release'),
        ('waiting_complete', 'Waiting Complete'),
        ('complete', 'Complete'),], help="Kondisi status record purchase request")
    action = fields.Selection(string='Action', required=True, selection=[
        ('pending_release', 'Pending Release'),
        ('waiting_release', 'Waiting Release'),
        ('waiting_complete', 'Waiting Complete'),
        ('complete', 'Complete'),], help="Action status selanjutnya pada record purchase request")
    company_unit_id = fields.Many2one('ics.company.unit', string='Allocation Approval', required=True, help="Filter akses approval hanya untuk user yang terdaftar pada unit tertentu")
    company_dept_id = fields.Many2one('ics.company.dept', string="Specific Allocation", required=True, help="Filter akses approval hanya untuk user yang terdaftar pada dept. tertentu")
    group_id = fields.Many2one('res.groups', string="Group Users", help="Membatasi akses approval hanya bisa dilakukan oleh user dalam group yang dipilih, jika kondisi unit dan dept. sama")
    multi_dept = fields.Boolean(string="Can Approve Other ?", default=False, help="Membuka akses dept. sehingga dapat melakukan approve dengan dept. yang berbeda dalam satu unit yang sama")

    @api.onchange('action')
    def _update_name(self):
        generate_name = dict(self._fields['action']._description_selection(self.env)).get(self.action)

        self.name = generate_name
