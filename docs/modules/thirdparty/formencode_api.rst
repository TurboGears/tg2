.. _formencode:

==========
FormEncode
==========

FormEncode is a validation and form generation package. The validation can be used separately from the form generation. The validation works on compound data structures, with all parts being nestable. It is separate from HTTP or any other input mechanism.

These module API docs are divided into section by category.

Core API
========

:mod:`formencode.api`
---------------------

These functions are used mostly internally by FormEncode.

.. automodule:: formencode.api

.. function:: is_validator(obj)

    Returns whether ``obj`` is a validator object or not.

.. autoclass:: Invalid
    :members:
    
    .. automethod:: __init__

.. autoclass:: Validator
    :members:

.. autoclass:: FancyValidator
    :members:


:mod:`formencode.schema`
------------------------

The FormEncode schema is one of the most important parts of using FormEncode,
as it lets you organize validators into parts that can be re-used between
schemas. Generally, a single schema will represent an entire form, but may
inherit other schemas for re-usable validation parts (ie, maybe multiple 
forms all requires first and last name).

.. module:: formencode.schema

.. autoclass:: Schema
.. autoclass:: SimpleFormValidator


Validators
==========

.. automodule:: formencode.validators

.. autoclass:: Bool
.. autoclass:: CIDR
.. autoclass:: CreditCardValidator
.. autoclass:: CreditCardExpires
.. autoclass:: CreditCardSecurityCode
.. autoclass:: DateConverter
.. autoclass:: DateValidator
.. autoclass:: DictConverter
.. autoclass:: Email
.. autoclass:: Empty
.. autoclass:: FieldsMatch
.. autoclass:: FieldStorageUploadConverter
.. autoclass:: FileUploadKeeper
.. autoclass:: FormValidator
.. autoclass:: IndexListConverter
.. autoclass:: Int
.. autoclass:: IPhoneNumberValidator
.. autoclass:: MACAddress
.. autoclass:: MaxLength
.. autoclass:: MinLength
.. autoclass:: Number
.. autoclass:: NotEmpty
.. autoclass:: OneOf
.. autoclass:: PhoneNumber
.. autoclass:: PlainText
.. autoclass:: PostalCode
.. autoclass:: Regex
.. autoclass:: RequireIfMissing
.. autoclass:: Set
.. autoclass:: SignedString
.. autoclass:: StateProvince
.. autoclass:: String
.. autoclass:: StringBool
.. autoclass:: StripField
.. autoclass:: TimeConverter
.. autoclass:: UnicodeString
.. autoclass:: URL


Wrapper Validators
------------------

.. autoclass:: ConfirmType
.. autoclass:: Wrapper
.. autoclass:: Constant


Validator Modifiers
===================

:mod:`formencode.compound`
--------------------------

.. automodule:: formencode.compound

.. autoclass:: Any

.. autoclass:: All


:mod:`formencode.foreach`
-------------------------

.. automodule:: formencode.foreach

.. autoclass:: ForEach


HTML Parsing and Form Filling
=============================

:mod:`formencode.htmlfill`
--------------------------

.. automodule:: formencode.htmlfill

.. autofunction:: render
.. autofunction:: default_formatter
.. autofunction:: none_formatter
.. autofunction:: escape_formatter
.. autofunction:: escapenl_formatter
.. autoclass:: FillingParser

