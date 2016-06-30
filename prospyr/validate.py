from marshmallow import validate


class WhitespaceEmail(validate.Email):
    """
    Email validator that permits surrounding whitespace.
    """

    def __call__(self, value):
        value = value.strip()
        super(WhitespaceEmail, self).__call__(value)
