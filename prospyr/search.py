# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from itertools import count, islice, tee
from logging import getLogger

from requests import codes

from prospyr import connection, exceptions

logger = getLogger(__name__)


class LazyCacheList(object):

    def __init__(self):
        self._results = self._results_generator()

    def _results_generator(self):
        """
        Subclasses should implement a generator here.
        """
        raise NotImplementedError()

    def __iter__(self):
        """
        Iterate resource instances. Results are cached.

        Depending on page size, this could result in many requests.
        """
        self._results, cpy = tee(self._results)
        return cpy

    def __getitem__(self, index):
        """
        Fetch the nth of sliceth item from cache or ProsperWorks.

        Fetching item N involves fetching items 0 through N-1. Depending on
        page size and N, this could be many requests.
        """
        negative = (
            type(index) is slice and (
                (index.start is not None and index.start < 0) or
                (index.stop is not None and index.stop < 0)
            ) or
            type(index) is not slice and index < 0
        )
        if negative:
            raise IndexError('ResultSet does not support negative indexing')

        self._results, cpy = tee(self._results)
        if type(index) is slice:
            return list(islice(cpy, index.start, index.stop, index.step))
        else:
            try:
                return next(islice(cpy, index, index+1))
            except StopIteration:
                raise IndexError('ResultSet index out of range')

    def __repr__(self):
        # show up to 5 results, then elipses. 6 results are fetched to
        # accomodate the elipses logic.
        first_6 = [str(r) for r in self[:6]]
        truncated = len(first_6) == 6
        if truncated:
            first_6 = first_6[0:5] + ['...']

        return '<{name}: {results}>'.format(
            name=type(self).__name__,
            results=', '.join(first_6)
        )


class ResultSet(LazyCacheList):
    """
    Immutable, lazy search results.
    """

    def __init__(self, resource_cls, params=None, order_field=None,
                 order_dir='asc', using='default', page_size=100):
        super(ResultSet, self).__init__()
        self._params = params or {}
        self._order_field = order_field
        self._order_dir = order_dir
        self._resource_cls = resource_cls
        self._using = using
        self._page_size = page_size

    def all(self):
        return self.filter()

    def filter(self, **query):
        new_params = self._params.copy()
        new_params.update(query)
        return ResultSet(params=new_params, using=self._using,
                         resource_cls=self._resource_cls,
                         order_field=self._order_field,
                         order_dir=self._order_dir, page_size=self._page_size)

    def order_by(self, field):
        dir = 'asc'
        if field.startswith('-'):
            dir, field = 'desc', field[1:]
        available = self._resource_cls.Meta.order_fields
        if field not in available:
            raise ValueError(
                'Cannot sort by `{field}`; try one of {valid}'
                .format(field=field, valid=', '.join(sorted(available)))
            )
        return ResultSet(params=self._params, using=self._using,
                         resource_cls=self._resource_cls, order_dir=dir,
                         order_field=field, page_size=self._page_size)

    @property
    def _conn(self):
        return connection.get(self._using)

    @property
    def _url(self):
        path = self._resource_cls.Meta.search_path
        return self._conn.build_absolute_url(path)

    def _build_query(self):
        query = dict(page_size=self._page_size, **self._params)
        if self._order_field:
            query.update({
                'sort_by': self._order_field,
                'sort_direction': self._order_dir,
            })
        return query

    def _results_generator(self):
        """
        Return Resource instances by querying ProsperWorks.

        You should not normally need to call this method directly.
        """
        query = self._build_query()

        for query['page_number'] in count(1):
            resp = self._conn.post(self._url, json=query)
            if resp.status_code != codes.ok:
                raise exceptions.ApiError(resp.status_code, resp.text)

            # no (more) results
            page_data = resp.json()
            logger.debug('%s results on page %s of %s',
                         len(page_data), query['page_number'], self._url)

            # 200 OK (not 404) and empty results if no more results
            if not page_data:
                break

            for data in page_data:
                yield self._resource_cls.from_api_data(data)

            # detect last page of results
            if len(page_data) < self._page_size:
                break


class ListSet(LazyCacheList):

    def __init__(self, resource_cls, using='default'):
        super(ListSet, self).__init__()
        self._resource_cls = resource_cls
        self._using = using

    @property
    def _conn(self):
        return connection.get(self._using)

    def _results_generator(self):
        path = self._resource_cls.Meta.list_path
        url = self._conn.build_absolute_url(path)
        resp = self._conn.get(url)

        if resp.status_code != codes.ok:
            raise exceptions.ApiError(resp.status_code, resp.text)

        for data in resp.json():
            yield self._resource_cls.from_api_data(data)

    def all(self):
        return self

    def filter(self, *args, **kwargs):
        raise NotImplementedError('ListSet does not support filtering')

    def order_by(self, *args, **kwargs):
        raise NotImplementedError('ListSet does not support ordering')
