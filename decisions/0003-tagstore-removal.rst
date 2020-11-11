Status
======

Accepted


Context
=======

During the initial development of Blockstore for the LabXchange project, a tagging service called tagstore was
developed to allow tagging XBlock content stored in Blockstore. However rapidly evolving product needs made it
very complicated to have a performant generic tagging system which could be used by multiple systems. Therefore
tagging functionality was added to the LabXchange backend service instead.


Decision
========

Tagstore code will be removed from the blockstore repo. If Studio or other services need the ability to tag XBlock or
other content a tagging system appropriate for the product needs can be developed.


Consequences
============

Since the tagstore is not being used there are no changes needed anywhere else.

Background
==========

* `Open edX Tagging Service Proposal <https://openedx.atlassian.net/wiki/spaces/AC/pages/791937307/Open+edX+Tagging+Service+Proposal>`_
