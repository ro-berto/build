# attrs

[attrs](https://www.attrs.org) is a python library that simplifies the process
of creating feature-rich classes in python. By decorating the class with
`attr.s` and defining attributes on the class using `attr.ib`, you get
`__init__`, `__repr__`, `__eq__` and the ordering operators defined
automatically. Optional features allow you to set the default values of the
attributes, make the class' instances frozen and provide validation and
conversion of the attribute values.

## Why not just use protos?

You might look at what *attrs* generates by default and think that you could get
the same benefits with protocol buffers. Protocol buffers do indeed provide you
the ability to easily create a class with `__init__`, `__repr__` and `__eq__`
operations, but notably you can't do the following:

* Specify default values for the fields
* Make the class' instances frozen
* Provide conversion for the attribute values
* Refer to python user-defined types
* Add additional methods or properties to the type

## What does this module provide?

This module provides `attrs` and `attrib`, constraints that can be used with
`attrib`, and some additional utilities. `attrs` and `attrib` are alternatives
to `attr.s` and `attr.ib` provided by *attrs*. Using these alternatives provides
the following benefits:

* Emphasis on immutability
* More flexibility in terms of required attributes and better exceptions when
  required attributes are not provided
* Earlier detection of bad default values
* More concise attribute declaration with boilerplate reduction for common
  combinations of validation and conversion, at the cost of some of the features
  provided by `attr.ib`

See the module documentation for more details.

Not all of the functionality provided by *attrs* is exposed via this module,
please contact the owners of this module if there is something that you think
should be added or updated.

Classes defined using `attrs` and `attrib` are fully compatible with the
[helpers](https://www.attrs.org/api.html#helpers) that *attrs* provides.
