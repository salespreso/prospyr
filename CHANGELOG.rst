Changelog
=========

0.8.0
-----

- Read-only support for Custom Fields.
- Add ``WebHook`` resource (soccernee)
- When a resource class raises validation errors, the message now includes the
  name of that class.
- Restructure modules so that circular dependencies are not so easy to cause.
  If you were importing ``Resource``, ``SecondaryResource``, or anything
  defines by ``prospyr.mixins``, they now live in ``prospyr.resource_base``. If
  you were importing ``Manager`` or any of its variants, they now live in
  ``prospyr.managers``.

0.7.0
-----

- Add ``Account`` resource (tizz98)
- Add ability to fetch Person by email as well as id (tizz98)

0.6.0
-----

- Add ``Lead`` resource (tizz98)

The Distant Past
-----------------

Everything else happened before the maintainer kept a changelog.
