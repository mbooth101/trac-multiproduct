# Welcome to MultiProduct

MultiProduct is a plug-in for Trac that adds basic multiple product support by allowing per-product components and versions.

This plug-in adds a new field type to Trac, depselect, which is a select field that depends on the value of another select field. Three new fields are then added to the ticket model:

 * Product - a normal select field and the parent field upon which the depselect fields depend.
 * Product Component and Product Version - depselect fields whose available values change depending on the value of the Product field.

The plug-in currently requires a patch to Trac itself in order to function, though I plan to eliminate that need in a future version.

## Installation and Usage

Because a patch must be applied to Trac before using this plug-in, Trac must be installed with the following commands instead of through the operating system's package manager:

    $ svn export http://svn.edgewall.org/repos/trac/tags/trac-<<VERSION>> trac
    $ svn export https://www.matbooth.co.uk/svn/trunk/multiproduct/patches/ patches
    $ cd trac/
    $ patch -p0 <../patches/depselect_support_trac-<<VERSION>>.patch
    $ python ./setup.py install

Where <<VERSION>> is your favourite version of Trac. Currently supported versions are 0.11.4, 0.11.5 and 0.11.6.

Now install the MultiProduct plug-in:

    $ easy_install -Z https://www.matbooth.co.uk/svn/trunk/multiproduct/

When the plug-in is enabled in trac.ini it is also recommended that you disable the admin plug-ins for the component and version fields, since MultiProduct is really a replacement for these fields:

    [components]
    multiproduct.* = enabled
    trac.ticket.admin.componentadminpanel = disabled
    trac.ticket.admin.versionadminpanel = disabled

The Trac environment will ask to be upgraded:

    $ trac-admin /path/to/trac/environment upgrade

Once configured, Trac administrators will find a new ticket system admin panel for each of the fields added by the plug-in.
