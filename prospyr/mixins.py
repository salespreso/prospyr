# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from requests import codes

from prospyr.exceptions import ApiError, ValidationError


class Creatable(object):
    """
    Allows creation of a Resource. Should be mixed in with that class.
    """

    # pworks uses 200 OK for creates. 201 CREATED is here through optimism.
    _create_success_codes = {codes.created, codes.ok}

    def create(self, using='default'):
        """
        Create a new instance of this Resource. True on success.
        """
        if hasattr(self, 'id'):
            raise ValueError(
                '%s cannot be created; it already has an id' % self
            )
        conn = self._get_conn(using)
        path = self.Meta.create_path

        # pworks does not want Nones, despite handing them out.
        data = {k: v for k, v in self._raw_data.items() if v is not None}

        resp = conn.post(conn.build_absolute_url(path), json=data)

        if resp.status_code in self._create_success_codes:
            data = self._data_from_resp(resp)
            self._set_fields(data)
            return True
        elif resp.status_code == codes.unprocessable_entity:
            error = resp.json()
            raise ValueError(error['message'])
        else:
            raise ApiError(resp.status_code, resp.text)


class Readable(object):
    """
    Allows reading of a Resource. Should be mixed in with that class.
    """

    _read_success_codes = {codes.ok}

    def read(self, using='default'):
        """
        Read this Resource from remote API. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s must be saved before it is read' % self)
        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)
        resp = conn.get(conn.build_absolute_url(path))
        if resp.status_code not in self._read_success_codes:
            raise ApiError(resp.status_code, resp.text)

        data = self._data_from_resp(resp)
        self._set_fields(data)
        return True


class Updateable(object):
    """
    Allows updating a Resource. Should be mixed in with that class.
    """

    _update_success_codes = {codes.ok}

    def update(self, using='default'):
        """
        Update this Resource. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s cannot be deleted before it is saved' % self)
        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)

        # pworks does not want Nones, despite handing them out.
        data = {k: v for k, v in self._raw_data.items() if v is not None}

        resp = conn.put(conn.build_absolute_url(path), json=data)
        if resp.status_code in self._update_success_codes:
            return True
        elif resp.status_code == codes.unprocessable_entity:
            error = resp.json()
            raise ValueError(error['message'])
        else:
            raise ApiError(resp.status_code, resp.text)


class Deletable(object):
    """
    Allows deletion of a Resource. Should be mixed in with that class.
    """

    _delete_success_codes = {codes.ok}

    def delete(self, using='default'):
        """
        Delete this Resource. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s cannot be deleted before it is saved' % self)
        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)
        resp = conn.delete(conn.build_absolute_url(path))
        if resp.status_code in self._delete_success_codes:
            return True
        else:
            raise ApiError(resp.status_code, resp.text)


class ReadWritable(Creatable, Readable, Updateable, Deletable):
    pass
