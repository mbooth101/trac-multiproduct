# Copyright (C) 2009 Mat Booth <mat@matbooth.co.uk>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from datetime import datetime

from trac.config import Option
from trac.core import *
from trac.db import Table, Column
from trac.resource import ResourceNotFound
from trac.ticket.api import TicketSystem, ITicketManipulator
from trac.ticket.model import simplify_whitespace
from trac.util import embedded_numbers, sorted
from trac.util.datefmt import utc, utcmax, to_timestamp
from trac.util.translation import _


class TicketExtensions(Component):
    """Provides some extensions to the ticket model behaviour,
    including extra validation."""

    implements(ITicketManipulator)

    # Config options

    default_product = Option('ticket', 'default_product', '',
        """Default product for newly created tickets.""")

    # ITicketManipulator methods

    def prepare_ticket(self, req, ticket, fields, actions):
        return None

    def validate_ticket(self, req, ticket):
        db = self.env.get_db_cnx()

        # Default the owner field to the product owner, if left blank
        if ticket.values.get('product') and not ticket.values.get('owner'):
            try:
                product = Product(self.env, ticket['product'], db=db)
                if product.owner:
                    ticket['owner'] = product.owner
            except ResourceNotFound, e:
                # No such product exists
                pass
        return []

class Product(object):

    _schema = [
        Table('multiproduct_product', key='name')[
            Column('name'),
            Column('owner'),
            Column('description'),
            ]
        ]

    def __init__(self, env, name=None, db=None):
        self.env = env
        if name:
            name = simplify_whitespace(name)
        if name:
            if not db:
                db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT owner,description FROM multiproduct_product "
                           "WHERE name=%s", (name,))
            row = cursor.fetchone()
            if not row:
                raise ResourceNotFound(_('Product %(name)s does not exist.',
                                  name=name))
            self.name = self._old_name = name
            self.owner = row[0] or None
            self.description = row[1] or ''
        else:
            self.name = self._old_name = None
            self.owner = None
            self.description = None

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self, db=None):
        assert self.exists, 'Cannot delete non-existent product'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Deleting product %s' % self.name)
        cursor.execute("DELETE FROM multiproduct_product WHERE name=%s", (self.name,))
        cursor.execute("DELETE FROM multiproduct_product_component WHERE parent=%s", (self.name,))
        cursor.execute("DELETE FROM multiproduct_product_version WHERE parent=%s", (self.name,))

        self.name = self._old_name = None

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def insert(self, db=None):
        assert not self.exists, 'Cannot insert existing product'
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot create product with no name'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.debug("Creating new product '%s'" % self.name)
        cursor.execute("INSERT INTO multiproduct_product (name,owner,description) "
                       "VALUES (%s,%s,%s)",
                       (self.name, self.owner, self.description))

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def update(self, db=None):
        assert self.exists, 'Cannot update non-existent product'
        self.name = simplify_whitespace(self.name)
        assert self.name, 'Cannot update product with no name'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Updating product "%s"' % self.name)
        cursor.execute("UPDATE multiproduct_product SET name=%s,owner=%s,description=%s "
                       "WHERE name=%s",
                       (self.name, self.owner, self.description,
                        self._old_name))
        if self.name != self._old_name:
            # Update tickets
            cursor.execute("UPDATE ticket SET product=%s WHERE product=%s",
                           (self.name, self._old_name))
            # Update dependent fields
            cursor.execute("UPDATE multiproduct_product_component SET parent=%s WHERE parent=%s", 
                           (self.name, self._old_name)) 
            cursor.execute("UPDATE multiproduct_product_version SET parent=%s WHERE parent=%s", 
                           (self.name, self._old_name))
            self._old_name = self.name

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def select(cls, env, db=None):
        if not db:
            db = env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT name,owner,description FROM multiproduct_product "
                       "ORDER BY name")
        for name, owner, description in cursor:
            product = cls(env)
            product.name = product._old_name = name
            product.owner = owner or None
            product.description = description or ''
            yield product
    select = classmethod(select)


class ProductComponent(object):

    _schema = [
        Table('multiproduct_product_component', key=('parent', 'name'))[
            Column('parent'),
            Column('name'),
            Column('description'),
            ]
        ]

    def __init__(self, env, name=None, parent=None, db=None):
        self.env = env
        if name:
            name = simplify_whitespace(name)
        if parent:
            parent = simplify_whitespace(parent)
        if name and parent:
            if not db:
                db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT description FROM multiproduct_product_component "
                           "WHERE name=%s AND parent=%s", (name, parent))
            row = cursor.fetchone()
            if not row:
                raise ResourceNotFound(_('Product component %(name)s does not exist for '
                                         'product %(parent)s',
                                         name=name, parent=parent))
            self.name = self._old_name = name
            self.parent = self._old_parent = parent
            self.description = row[0] or ''
        else:
            self.name = self._old_name = None
            self.parent = self._old_parent = None
            self.description = None

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self, db=None):
        assert self.exists, 'Cannot delete non-existent product component'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Deleting product component %s' % self.name)
        cursor.execute("DELETE FROM multiproduct_product_component WHERE name=%s AND parent=%s",
                       (self.name, self.parent))

        self.name = self._old_name = None
        self.parent = self._old_parent = None

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def insert(self, db=None):
        assert not self.exists, 'Cannot insert existing product component'
        self.name = simplify_whitespace(self.name)
        self.parent = simplify_whitespace(self.parent)
        assert self.name, 'Cannot create product component with no name'
        assert self.parent, 'Cannot create product component with no parent'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.debug("Creating new product component '%s'" % self.name)
        cursor.execute("INSERT INTO multiproduct_product_component (name,description,parent) "
                       "VALUES (%s,%s,%s)", (self.name, self.description, self.parent))

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def update(self, db=None):
        assert self.exists, 'Cannot update non-existent product component'
        self.name = simplify_whitespace(self.name)
        self.parent = simplify_whitespace(self.parent)
        assert self.name, 'Cannot update product component with no name'
        assert self.parent, 'Cannot update product component with no parent'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Updating product component "%s"' % self.name)
        cursor.execute("UPDATE multiproduct_product_component SET name=%s,description=%s,parent=%s "
                       "WHERE name=%s AND parent=%s",
                       (self.name, self.description, self.parent,
                        self._old_name, self._old_parent))
        if self.name != self._old_name or self.parent != self._old_parent:
            # Update tickets
            cursor.execute("UPDATE ticket SET product=%s, product_component=%s "
                           "WHERE product=%s AND product_component=%s",
                           (self.parent, self.name, self._old_parent, self._old_name))
            self._old_name = self.name
            self._old_parent = self.parent

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def select(cls, env, db=None, parent=None):
        if not db:
            db = env.get_db_cnx()
        cursor = db.cursor()
        if parent:
            cursor.execute("SELECT name,parent,description FROM multiproduct_product_component "
                           "WHERE parent=%s ORDER BY name", (parent,))
        else:
            cursor.execute("SELECT name,parent,description FROM multiproduct_product_component "
                           "ORDER BY parent,name")
        for name, parent, description in cursor:
            prodcomp = cls(env)
            prodcomp.name = prodcomp._old_name = name
            prodcomp.parent = prodcomp._old_parent = parent
            prodcomp.description = description or ''
            yield prodcomp
    select = classmethod(select)


class ProductVersion(object):

    _schema = [
        Table('multiproduct_product_version', key=('parent', 'name'))[
            Column('parent'),
            Column('name'),
            Column('time', type='int'),
            Column('description'),
            ]
        ]

    def __init__(self, env, name=None, parent=None, db=None):
        self.env = env
        if name:
            name = simplify_whitespace(name)
        if parent:
            parent = simplify_whitespace(parent)
        if name and parent:
            if not db:
                db = self.env.get_db_cnx()
            cursor = db.cursor()
            cursor.execute("SELECT time,description FROM multiproduct_product_version "
                           "WHERE name=%s AND parent=%s", (name, parent))
            row = cursor.fetchone()
            if not row:
                raise ResourceNotFound(_('Product version %(name)s does not exist for '
                                         'product %(parent)s',
                                         name=name, parent=parent))
            self.name = self._old_name = name
            self.parent = self._old_parent = parent
            self.time = row[0] and datetime.fromtimestamp(int(row[0]), utc) or None
            self.description = row[1] or ''
        else:
            self.name = self._old_name = None
            self.parent = self._old_parent = None
            self.time = None
            self.description = None

    exists = property(fget=lambda self: self._old_name is not None)

    def delete(self, db=None):
        assert self.exists, 'Cannot delete non-existent product version'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Deleting product version %s' % self.name)
        cursor.execute("DELETE FROM multiproduct_product_version WHERE name=%s AND parent=%s",
                       (self.name, self.parent))

        self.name = self._old_name = None
        self.parent = self._old_parent = None

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def insert(self, db=None):
        assert not self.exists, 'Cannot insert existing product version'
        self.name = simplify_whitespace(self.name)
        self.parent = simplify_whitespace(self.parent)
        assert self.name, 'Cannot create product version with no name'
        assert self.parent, 'Cannot create product version with no parent'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.debug("Creating new product version '%s'" % self.name)
        cursor.execute("INSERT INTO multiproduct_product_version (name,time,description,parent) "
                       "VALUES (%s,%s,%s,%s)", (self.name, to_timestamp(self.time), self.description, self.parent))

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def update(self, db=None):
        assert self.exists, 'Cannot update non-existent product version'
        self.name = simplify_whitespace(self.name)
        self.parent = simplify_whitespace(self.parent)
        assert self.name, 'Cannot update product version with no name'
        assert self.parent, 'Cannot update product version with no parent'
        if not db:
            db = self.env.get_db_cnx()
            handle_ta = True
        else:
            handle_ta = False

        cursor = db.cursor()
        self.env.log.info('Updating product version "%s"' % self.name)
        cursor.execute("UPDATE multiproduct_product_version SET name=%s,time=%s,description=%s,parent=%s "
                       "WHERE name=%s AND parent=%s",
                       (self.name, to_timestamp(self.time), self.description, self.parent,
                        self._old_name, self._old_parent))
        if self.name != self._old_name or self.parent != self._old_parent:
            # Update tickets
            cursor.execute("UPDATE ticket SET product=%s, product_version=%s "
                           "WHERE product=%s AND product_version=%s",
                           (self.parent, self.name, self._old_parent, self._old_name))
            self._old_name = self.name
            self._old_parent = self.parent

        if handle_ta:
            db.commit()
        TicketSystem(self.env).reset_ticket_fields()

    def select(cls, env, db=None, parent=None):
        if not db:
            db = env.get_db_cnx()
        cursor = db.cursor()
        if parent:
            cursor.execute("SELECT name,parent,time,description FROM multiproduct_product_version "
                           "WHERE parent=%s", (parent,))
        else:
            cursor.execute("SELECT name,parent,time,description FROM multiproduct_product_version")
        versions = []
        for name, parent, time, description in cursor:
            prodversion = cls(env)
            prodversion.name = prodversion._old_name = name
            prodversion.parent = prodversion._old_parent = parent
            prodversion.time = time and datetime.fromtimestamp(int(time), utc) or None
            prodversion.description = description or ''
            versions.append(prodversion)
        def version_order(v):
            return (v.time or utcmax, embedded_numbers(v.name))
        return sorted(versions, key=version_order, reverse=True)
    select = classmethod(select)


schema_ver = 1
schema = Product._schema + ProductComponent._schema + ProductVersion._schema
