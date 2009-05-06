# Copyright (C) 2009 Mat Booth <mat@matbooth.co.uk>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

import re

from trac.core import *
from trac.perm import PermissionSystem
from trac.resource import ResourceNotFound
from trac.ticket.admin import TicketAdminPanel
from trac.util.datefmt import parse_date, get_date_format_hint, get_datetime_format_hint
from trac.util.translation import _
from trac.web.chrome import add_script

from multiproduct import model


class ProductAdminPanel(TicketAdminPanel):
    """Provides an admin panel for Products."""

    _type = 'products'
    _label = ('Product', 'Products')

    # TicketAdminPanel methods

    def _render_admin_panel(self, req, cat, page, product):
        # Detail view?
        if product:
            prod = model.Product(self.env, product)
            if req.method == 'POST':
                if req.args.get('save'):
                    prod.name = req.args.get('name')
                    prod.owner = req.args.get('owner')
                    prod.description = req.args.get('description')
                    prod.update()
                    req.redirect(req.href.admin(cat, page))
                elif req.args.get('cancel'):
                    req.redirect(req.href.admin(cat, page))

            add_script(req, 'common/js/wikitoolbar.js')
            data = {'view': 'detail', 'field': prod}

        else:
            if req.method == 'POST':
                # Add Product
                if req.args.get('add') and req.args.get('name'):
                    name = req.args.get('name')
                    try:
                        model.Product(self.env, name=name)
                    except ResourceNotFound:
                        prod = model.Product(self.env)
                        prod.name = name
                        if req.args.get('owner'):
                            prod.owner = req.args.get('owner')
                        prod.insert()
                        req.redirect(req.href.admin(cat, page))
                    else:
                        raise TracError(_('Product %s already exists.') % name)

                # Remove products
                elif req.args.get('remove'):
                    sel = req.args.get('sel')
                    if not sel:
                        raise TracError(_('No product selected'))
                    if not isinstance(sel, list):
                        sel = [sel]
                    db = self.env.get_db_cnx()
                    for name in sel:
                        prod = model.Product(self.env, name, db=db)
                        prod.delete(db=db)
                    db.commit()
                    req.redirect(req.href.admin(cat, page))

                # Set default product
                elif req.args.get('apply'):
                    if req.args.get('default'):
                        name = req.args.get('default')
                        self.log.info('Setting default product to %s', name)
                        self.config.set('ticket', 'default_product', name)
                        self.config.save()
                        req.redirect(req.href.admin(cat, page))

            default = self.config.get('ticket', 'default_product')
            data = {'view': 'list',
                    'products': list(model.Product.select(self.env)),
                    'default': default}

        if self.config.getbool('ticket', 'restrict_owner'):
            perm = PermissionSystem(self.env)
            def valid_owner(username):
                return perm.get_user_permissions(username).get('TICKET_MODIFY')
            data['owners'] = [username for username, name, email
                              in self.env.get_known_users()
                              if valid_owner(username)]
            data['owners'].insert(0, '')
            data['owners'].sort()
        else:
            data['owners'] = None

        data['label_singular'] = self._label[0]
        data['label_plural'] = self._label[1]
        return 'admin_products.html', data


class ProductComponentAdminPanel(TicketAdminPanel):
    """Provides an admin panel for Product Components."""

    _type = 'productcomponents'
    _label = ('Product Component', 'Product Components')

    # TicketAdminPanel methods

    def _render_admin_panel(self, req, cat, page, productcomponent):
        # Look for pattern <product>/<productcomponent> in url
        match = None
        if productcomponent:
            match = re.match('([^/]+)/(.*)$', productcomponent)

        # Detail view?
        if match:
            prodcomp = model.ProductComponent(self.env, match.group(2), match.group(1))
            if req.method == 'POST':
                if req.args.get('save'):
                    prodcomp.name = req.args.get('name')
                    prodcomp.owner = req.args.get('owner')
                    prodcomp.description = req.args.get('description')
                    prodcomp.update()
                    req.redirect(req.href.admin(cat, page, match.group(1)))
                elif req.args.get('cancel'):
                    req.redirect(req.href.admin(cat, page, match.group(1)))

            add_script(req, 'common/js/wikitoolbar.js')
            data = {'view': 'detail', 'field': prodcomp}

        else:
            if req.method == 'POST':
                # Add product component
                if req.args.get('add') and req.args.get('name') and req.args.get('parent'):
                    name = req.args.get('name')
                    parent = req.args.get('parent')
                    try:
                        model.ProductComponent(self.env, name=name, parent=parent)
                    except ResourceNotFound:
                        prodcomp = model.ProductComponent(self.env)
                        prodcomp.name = name
                        prodcomp.parent = parent
                        if req.args.get('owner'):
                            prodcomp.owner = req.args.get('owner')
                        prodcomp.insert()
                        req.redirect(req.href.admin(cat, page, prodcomp.parent))
                    else:
                        raise TracError(_('Product component %s already exists.') % name)

                # Remove product components
                elif req.args.get('remove'):
                    sel = req.args.get('sel')
                    parent = req.args.get('parent')
                    if not sel:
                        raise TracError(_('No product component selected'))
                    if not isinstance(sel, list):
                        sel = [sel]
                    db = self.env.get_db_cnx()
                    for name in sel:
                        prodcomp = model.ProductComponent(self.env, name, parent, db=db)
                        prodcomp.delete(db=db)
                    db.commit()
                    req.redirect(req.href.admin(cat, page, parent))

                # Change selected parent product
                elif req.args.get('parent'):
                    req.redirect(req.href.admin(cat, page, req.args.get('parent')))

            products = list(model.Product.select(self.env))
            if productcomponent:
                parent = productcomponent # Catches redirects
            else:
                parent = products[0].name or None # Just use the first in the list as default

            data = {
                'view': 'list',
                'products': products,
                'productcomponents': list(model.ProductComponent.select(self.env, parent=parent)),
                'parent': parent,
                }

        data['label_singular'] = self._label[0]
        data['label_plural'] = self._label[1]
        return 'admin_productcomponents.html', data


class ProductVersionAdminPanel(TicketAdminPanel):
    """Provides an admin panel for Product Versions."""

    _type = 'productversions'
    _label = ('Product Version', 'Product Versions')

    # TicketAdminPanel methods

    def _render_admin_panel(self, req, cat, page, productversion):
        # Look for pattern <product>/<productversion> in url
        match = None
        if productversion:
            match = re.match('([^/]+)/(.*)$', productversion)

        # Detail view?
        if match:
            prodver = model.ProductVersion(self.env, match.group(2), match.group(1))
            if req.method == 'POST':
                if req.args.get('save'):
                    prodver.name = req.args.get('name')
                    if req.args.get('time'):
                        prodver.time = parse_date(req.args.get('time'), req.tz)
                    else:
                        prodver.time = None # unset
                    prodver.description = req.args.get('description')
                    prodver.update()
                    req.redirect(req.href.admin(cat, page, match.group(1)))
                elif req.args.get('cancel'):
                    req.redirect(req.href.admin(cat, page, match.group(1)))

            add_script(req, 'common/js/wikitoolbar.js')
            data = {'view': 'detail', 'field': prodver}

        else:
            if req.method == 'POST':
                # Add product version
                if req.args.get('add') and req.args.get('name') and req.args.get('parent'):
                    name = req.args.get('name')
                    parent = req.args.get('parent')
                    try:
                        model.ProductVersion(self.env, name=name, parent=parent)
                    except ResourceNotFound:
                        prodver = model.ProductVersion(self.env)
                        prodver.name = name
                        prodver.parent = parent
                        if req.args.get('time'):
                            prodver.time = parse_date(req.args.get('time'), req.tz)
                        prodver.insert()
                        req.redirect(req.href.admin(cat, page, prodver.parent))
                    else:
                        raise TracError(_('Product version %s already exists.') % name)

                # Remove product versions
                elif req.args.get('remove'):
                    sel = req.args.get('sel')
                    parent = req.args.get('parent')
                    if not sel:
                        raise TracError(_('No product version selected'))
                    if not isinstance(sel, list):
                        sel = [sel]
                    db = self.env.get_db_cnx()
                    for name in sel:
                        prodver = model.ProductVersion(self.env, name, parent, db=db)
                        prodver.delete(db=db)
                    db.commit()
                    req.redirect(req.href.admin(cat, page, parent))

                # Change selected parent product
                elif req.args.get('parent'):
                    req.redirect(req.href.admin(cat, page, req.args.get('parent')))

            products = list(model.Product.select(self.env))
            if productversion:
                parent = productversion # Catches redirects
            else:
                parent = products[0].name or None # Just use the first in the list as default

            data = {
                'view': 'list',
                'products': products,
                'productversions': list(model.ProductVersion.select(self.env, parent=parent)),
                'parent': parent,
                }

        data['datetime_hint'] = get_datetime_format_hint()
        data['label_singular'] = self._label[0]
        data['label_plural'] = self._label[1]
        return 'admin_productversions.html', data
