import json
import sys
from voluptuous import In, Length, Match, Optional, Range, Required, Schema
from voluptuous.validators import ExactSequence, \
                                  _WithSubValidators as Validator
from CPAC.pipeline.schema import schema


def schema_to_json(schema_dict, filepath=None):
    """Function to parse a Voluptuous schema dictionary and save a
    JSON representation.

    Parameters
    ----------
    schema_dict : dict or any
        Call the function with a dict, recurses through other types

    filepath : string or None
        Saves to a file if a filepath is given

    Returns
    -------
    json_string : str

    Examples
    --------
    >>> from voluptuous import Schema
    >>> from voluptuous.validators import Maybe
    >>> schema_to_json(Schema({'FROM': Maybe(str)}))
    {'FROM': {'Any': ('str', None)}}
    """

    if isinstance(schema_dict, dict):
        return {
            str(k) if isinstance(k, (Optional, Required)) else
            getattr(k, '__name__', str(k)) if
            isinstance(k, type) else k: schema_to_json(
                schema_dict[k]
            ) for k in schema_dict
        }
    if isinstance(schema_dict, (ExactSequence, Validator)):
        return {
            schema_dict.__class__.__name__: schema_to_json(
                schema_dict.validators
            )
        }
    if isinstance(schema_dict, (Optional, Required)):
        return schema_to_json(schema_dict.schema)
    if isinstance(schema_dict, In):
        return {'In': schema_to_json(schema_dict.container)}
    if isinstance(schema_dict, (Length, Range)):
        return str(schema_dict)
    if isinstance(schema_dict, Match):
        return {'pattern': schema_dict.pattern.pattern}
    if isinstance(schema_dict, tuple):
        return tuple(schema_to_json(item) for item in schema_dict)
    if isinstance(schema_dict, list):
        return [schema_to_json(item) for item in schema_dict]
    if isinstance(schema_dict, set):
        return {'set': list(schema_dict)}
    if isinstance(schema_dict, type):
        return getattr(schema_dict, '__name__', str(schema_dict))
    if isinstance(schema_dict, Schema):
        return schema_to_json(schema_dict.schema)
    if filepath is not None:
        json.dump(schema_dict, filepath)
    else:
        return json.dumps(schema_dict)


if __name__ == '__main__':
    schema_to_json(schema.schema, sys.argv[1])
