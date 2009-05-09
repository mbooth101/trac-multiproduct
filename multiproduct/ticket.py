# Copyright (C) 2009 Mat Booth <mat@matbooth.co.uk>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from genshi.builder import tag
from genshi.filters import Transformer

from trac.core import *
from trac.config import Option
from trac.ticket.api import ITicketManipulator
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import add_script

from multiproduct import model

__all__ = ['TicketExtensions']


class TicketExtensions(Component):
    """Provides some extensions to the ticket model behaviour."""

    implements(ITicketManipulator, ITemplateStreamFilter)

    # Config options

    default_product = Option('ticket', 'default_product', '',
        """Default product for newly created tickets.""")

    # ITicketManipulator methods

    def prepare_ticket(self, req, ticket, fields, actions):
        """Not used."""
        return None

    def validate_ticket(self, req, ticket):
        """Used to default the owner field to the product owner, if it's left blank by
        the user."""

        db = self.env.get_db_cnx()

        if ticket.values.get('product') and not ticket.values.get('owner'):
            try:
                product = model.Product(self.env, ticket['product'], db=db)
                if product.owner:
                    ticket['owner'] = product.owner
                    self.log.info("Setting ticket owner to product owner")
            except ResourceNotFound, e:
                # Don't bother if the product doesn't exist
                pass
        return []

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        """This extension point is used to make hidden duplicates of depselect fields
        in the ticket template.  We do this to get around some CSS difficulties in
        Internet Explorer, see the comments in the ticket_depselect_fettler.js for more
        details."""

        if not filename == 'ticket.html':
            return stream

        # Iterate through the list of all the depselect fields
        for d in [f for f in data['fields'] if f['type'] == 'depselect']:

            # Add a hidden select for every depselect field
            elm = tag.select(style="display: none", id='field-%s%s' % (d['parent'], d['name']))
            if d['optional']:
                elm(tag.option)
            ticket_val = data['ticket'].get_value_or_default(d['name'])
            for val, parent_val in d['options']:
                if ticket_val == val:
                    elm(tag.option(val, class_=parent_val, selected='selected'))
                else:
                    elm(tag.option(val, class_=parent_val))
            stream |= Transformer('.//body').append(elm)

        add_script(req, 'multiproduct/js/ticket_depselect_fettler.js')
        return stream
