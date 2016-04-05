Prospyr
=======

A Python client library for ProsperWorks.

.. image:: https://api.travis-ci.org/salespreso/prospyr.svg?branch=master
   :target: https://travis-ci.org/salespreso/prospyr
   :alt: Prospyr builds

.. image:: https://img.shields.io/pypi/v/prospyr.svg
   :target: https://pypi.python.org/pypi/prospyr/
   :alt: Prospyr on Pypi.

Usage
=====

.. code-block:: python

    from prospyr import connect, resources

    # see https://www.prosperworks.com/developer_api/token_generation to obtain
    # a token.
    cn = connect(email='user@domain.tld', token='1aefcc3...')

    # collections can be ordered and sliced.
    newest_person = resources.Person.objects.order_by('-date_modified')[0]

    # new records can be created.
    art = resources.Person(
        name='Art Vandelay',
        emails=[{'email': 'art@vandelayindustries.net', 'category': 'work'}]
    )
    art.create()  # Art is local-only until .create() is called

    # related objects can be read and assigned
    art.company = resources.Company.objects.all()[0]
    art.update()

    # and deleting works too.
    art.delete()

Installation
============

.. code-block:: shell

    pip install prospyr
