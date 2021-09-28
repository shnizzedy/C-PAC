import json
import sys
from voluptuous import In, Length, Match, Optional, Range, Required, Schema
from voluptuous.validators import ExactSequence, \
                                  _WithSubValidators as Validator
from CPAC.pipeline.schema import schema


def schema_to_json(schema_dict):
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
    dict
        JSON serializable dictionary

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
        return {'type': getattr(schema_dict, '__name__', str(schema_dict))}
    if isinstance(schema_dict, Schema):
        return schema_to_json(schema_dict.schema)
    return schema_dict


if __name__ == '__main__':
    s2j = schema_to_json(schema.schema)
    if len(sys.argv) > 1 and sys.argv[1] is not None:
        json.dump(s2j, open(sys.argv[1], 'w'), indent=2)
    else:
        print(json.dumps(s2j))
