from odoo import models, fields, api

class IcsApprovalPRWizard(models.TransientModel):
    _name = 'ics.approval.pr.wizard'
    _description = 'wizard approval for purchase request'

    request = fields.Many2one('purchase.request', string='Purchase Request', default=lambda self: self._context.get('active_id'))
    domain_filter = fields.Char(string='Filter Action', compute='get_user_action')
    actions = fields.Many2one('ics.approval.pr.rule', string='Action', required=True)

    @api.depends('request')
    def get_user_action(self):
        rules = self.env['ics.approval.pr.rule'].search([
            ('state', '=', self.request.state),
            ('company_unit_ids', 'in', [self.request.company_unit_id.id, self.request.company_unit_id.parent_id.id]),
        ])
        
        ids = []

        for rule in rules:
            xml_domain = [('model', '=', 'res.groups'), ('res_id', '=', rule.group_id.id)]
            xml_data   = self.env['ir.model.data'].sudo().search(xml_domain, limit=1)
            xml_id     = "%s.%s" % (xml_data.module, xml_data.name)

            if self.env.user.has_group(xml_id) and self.env.user.company_unit_id.id == rule.company_unit_ids.id:
                if self.request.requested_by.company_dept_id.id in rule.company_dept_ids.ids and self.request.requested_by.company_dept_id.id == self.env.user.company_dept_id.id:
                    ids.append(rule.id)
                elif rule.multi_dept:
                    ids.append(rule.id)

        self.domain_filter = [('id', 'in', ids)]

    def _write_approval_log(self):
        history = self.env['ics.approval.pr.log']

        if self.request.state not in ('sent', 'to_approve'):
            history.create({
                'request_id' : self.request.id,
                'approver_id': self.env.uid,
                'from_action': dict(self.request._fields['state'].selection).get(self.request.state),
                'to_action'  : self.actions.name,
            })

    def approve_purchase_request(self):
        action = self.actions.action
        rules  = self.env['ics.approval.pr.rule'].search([
            ('state', '=', action),
            ('company_unit_ids', '=', self.request.company_unit_id.id),
            ('company_dept_ids', '=', self.request.requested_by.company_dept_id.id)
        ])

        emails = []
        for rule in rules:
            xml_domain = [('model', '=', 'res.groups'), ('res_id', '=', rule.group_id.id)]
            xml_data   = self.env['ir.model.data'].sudo().search(xml_domain, limit=1)
            xml_id     = "%s.%s" % (xml_data.module, xml_data.name)
            users = self.env['res.users'].search([])

            for user in users:
                if user.has_group(xml_id) and rule.company_unit_id == user.company_unit_id and rule.company_dept_id == user.company_dept_id:
                    emails.append(user.login)

        recipient = ','.join(emails)

        ctx = {
            'status': self.actions.name
        }

        if len(recipient) > 0:
            template = self.env.ref('ics_purchase_request.approval_pr_mail_template')
            template.sudo().write({'email_to': recipient, 'email_cc': 'taufik@ics-seafood.com'})
            template.sudo().with_context(ctx).send_mail(self.request.id, force_send=False)

        self._write_approval_log()

        if action == 'waiting_complete':
            params = {
                'checker_id': self.env.uid,
                'state': action
            }
        else:
            params = {'state': action}

        if action == 'complete':
            return self.request.button_approved()
        else:
            return self.request.write(params)