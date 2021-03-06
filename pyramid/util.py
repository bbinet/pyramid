import inspect
import weakref

from pyramid.compat import (
    integer_types,
    string_types,
    text_,
    PY3,
    )

from pyramid.path import DottedNameResolver as _DottedNameResolver

class DottedNameResolver(_DottedNameResolver):
    def __init__(self, package=None): # default to package = None for bw compat
        return _DottedNameResolver.__init__(self, package)

class WeakOrderedSet(object):
    """ Maintain a set of items.

    Each item is stored as a weakref to avoid extending their lifetime.

    The values may be iterated over or the last item added may be
    accessed via the ``last`` property.

    If items are added more than once, the most recent addition will
    be remembered in the order:

        order = WeakOrderedSet()
        order.add('1')
        order.add('2')
        order.add('1')

        list(order) == ['2', '1']
        order.last == '1'
    """

    def __init__(self):
        self._items = {}
        self._order = []

    def add(self, item):
        """ Add an item to the set."""
        oid = id(item)
        if oid in self._items:
            self._order.remove(oid)
            self._order.append(oid)
            return
        ref = weakref.ref(item, lambda x: self.remove(item))
        self._items[oid] = ref
        self._order.append(oid)

    def remove(self, item):
        """ Remove an item from the set."""
        oid = id(item)
        if oid in self._items:
            del self._items[oid]
            self._order.remove(oid)

    def empty(self):
        """ Clear all objects from the set."""
        self._items = {}
        self._order = []

    def __len__(self):
        return len(self._order)

    def __contains__(self, item):
        oid = id(item)
        return oid in self._items

    def __iter__(self):
        return (self._items[oid]() for oid in self._order)

    @property
    def last(self):
        if self._order:
            oid = self._order[-1]
            return self._items[oid]()

def strings_differ(string1, string2):
    """Check whether two strings differ while avoiding timing attacks.

    This function returns True if the given strings differ and False
    if they are equal.  It's careful not to leak information about *where*
    they differ as a result of its running time, which can be very important
    to avoid certain timing-related crypto attacks:

        http://seb.dbzteam.org/crypto/python-oauth-timing-hmac.pdf

    """
    if len(string1) != len(string2):
        return True

    invalid_bits = 0
    for a, b in zip(string1, string2):
        invalid_bits += a != b

    return invalid_bits != 0

def object_description(object):
    """ Produce a human-consumable text description of ``object``,
    usually involving a Python dotted name. For example:

    .. code-block:: python

       >>> object_description(None)
       u'None'
       >>> from xml.dom import minidom
       >>> object_description(minidom)
       u'module xml.dom.minidom'
       >>> object_description(minidom.Attr)
       u'class xml.dom.minidom.Attr'
       >>> object_description(minidom.Attr.appendChild)
       u'method appendChild of class xml.dom.minidom.Attr'
       >>> 

    If this method cannot identify the type of the object, a generic
    description ala ``object <object.__name__>`` will be returned.

    If the object passed is already a string, it is simply returned.  If it
    is a boolean, an integer, a list, a tuple, a set, or ``None``, a
    (possibly shortened) string representation is returned.
    """
    if isinstance(object, string_types):
        return text_(object)
    if isinstance(object, integer_types):
        return text_(str(object))
    if isinstance(object, (bool, float, type(None))):
        return text_(str(object))
    if isinstance(object, set):
        if PY3: # pragma: no cover
            return shortrepr(object, '}')
        else:
            return shortrepr(object, ')')
    if isinstance(object, tuple):
        return shortrepr(object, ')')
    if isinstance(object, list):
        return shortrepr(object, ']')
    if isinstance(object, dict):
        return shortrepr(object, '}')
    module = inspect.getmodule(object)
    if module is None:
        return text_('object %s' % str(object))
    modulename = module.__name__
    if inspect.ismodule(object):
        return text_('module %s' % modulename)
    if inspect.ismethod(object):
        oself = getattr(object, '__self__', None)
        if oself is None: # pragma: no cover
            oself = getattr(object, 'im_self', None)
        return text_('method %s of class %s.%s' %
                     (object.__name__, modulename,
                      oself.__class__.__name__))
    
    if inspect.isclass(object):
        dottedname = '%s.%s' % (modulename, object.__name__)
        return text_('class %s' % dottedname)
    if inspect.isfunction(object):
        dottedname = '%s.%s' % (modulename, object.__name__)
        return text_('function %s' % dottedname)
    return text_('object %s' % str(object))

def shortrepr(object, closer):
    r = str(object)
    if len(r) > 100:
        r = r[:100] + ' ... %s' % closer
    return r
