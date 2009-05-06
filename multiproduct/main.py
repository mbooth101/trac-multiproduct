# Copyright (C) 2009 Mat Booth <mat@matbooth.co.uk>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

from trac.core import *
from trac.db import DatabaseManager
from trac.env import IEnvironmentSetupParticipant
from trac.web.chrome import ITemplateProvider

from multiproduct.model import schema, schema_ver


class MultiProductPlugin(Component):
    """Main plugin component."""

    implements(IEnvironmentSetupParticipant, ITemplateProvider)

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('multiproduct', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    # IEnvironmentSetupParticipant methods

    def environment_created(self):
        db = self.env.get_db_cnx()
        connector, _ = DatabaseManager(self.env)._get_connector()
        cursor = db.cursor()

        # Create new database schema
        for table in schema:
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

        # Extend existing schema
        cursor.execute("ALTER TABLE ticket ADD COLUMN product TEXT")
        cursor.execute("ALTER TABLE ticket ADD COLUMN product_component TEXT")
        cursor.execute("ALTER TABLE ticket ADD COLUMN product_version TEXT")

        # Insert a schema version flag
        cursor.execute("INSERT INTO system (name,value) VALUES ('multiproduct_version',%s)",
                       (schema_ver,))

        db.commit()

    def environment_needs_upgrade(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name='multiproduct_version'")
        row = cursor.fetchone()
        if not row or int(row[0]) < schema_ver:
            return True

    def upgrade_environment(self, db):
        cursor = db.cursor()
        cursor.execute("SELECT value FROM system WHERE name='multiproduct_version'")
        row = cursor.fetchone()
        if not row:
            self.environment_created()
        else:
            current_version = int(row[0])
            from multiproduct import upgrades
            for version in range(current_version + 1, schema_ver + 1):
                for function in upgrades.map.get(version):
                    print textwrap.fill(inspect.getdoc(function))
                    function(self.env, db)
                    print 'Done.'

            # Update the schema version flag
            cursor.execute("UPDATE system SET value=%s WHERE name='multiproduct_version'",
                           (schema_ver,))
            self.log.info('Upgraded MultiProduct tables from version %d to %d',
                          current_version, schema_ver)
