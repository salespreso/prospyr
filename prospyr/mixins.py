# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from requests import codes

from prospyr.exceptions import ApiError, ValidationError


class Creatable(object):
    """
    Allows creation of a Resource. Should be mixed in with that class.
    """

    def create(self, using='default'):
        """
        Create a new instance of this Resource. True on success.
        """
        conn = self._get_conn(using)
        if hasattr(self, 'id'):
            raise ValueError('% cannot be created; it already '
                             'has an id' & self._title)
        resp = conn.post(self._list_url, data=dumps(self._data))
        if resp.status_code == codes.created:
            self.set_fields(resp.json())
            return True
        else:
            raise ApiError(resp.status_code, resp.content)


class Readable(object):
    """
    Allows reading of a Resource. Should be mixed in with that class.
    """

    def read(self, using='default'):
        """
        Read this Resource from remote API. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s must be saved before it is read' % self)
        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)
        resp = conn.get(conn.build_absolute_url(path))
        if resp.status_code != codes.ok:
            raise ApiError(resp.status_code, resp.text)

        data, errors = self.Meta.schema.loads(resp.text)
        if errors:
            raise ValidationError(
                'ProsperWorks delivered data which does not agree with the '
                'local prospyr schema. Errors encountered: %s' % repr(errors)
            )

        self._set_fields(data)
        return True


class Updateable(object):
    """
    Allows updating a Resource. Should be mixed in with that class.
    """

    def update(self, using='default'):
        """
        Update this Resource. True on success.
        """
        try:
            url = self._detail_url
        except ValueError:
            raise ValueError('% cannot be updated '
                             'before it is saved' % self._title)
        conn = self._get_conn(using)
        data = self.schema.dump(self._data).data
        resp = conn.put(url, json=data)
        import ipdb; ipdb.set_trace()
        if resp.status_code == codes.ok:
            self.set_fields(resp.json())
            return True
        else:
            raise ApiError(resp.status_code, resp.content)


class Deletable(object):
    """
    Allows deletion of a Resource. Should be mixed in with that class.
    """

    def delete(self, using='default'):
        """
        Delete this Resource. True on success.
        """
        try:
            url = self._detail_url
        except ValueError:
            raise ValueError('% cannot be deleted '
                             'before it is saved' % self._title)
        conn = self._get_conn(using)
        resp = conn.delete(url)
        if resp.status_code == requests.codes.no_content:
            return True
        else:
            raise ApiError(resp.status_code, resp.body)


class ReadWritable(Creatable, Readable, Updateable, Deletable):
    pass
