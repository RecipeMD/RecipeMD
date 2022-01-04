import copy
from enum import Enum
from pprint import pp, pprint
from typing import Any, Callable, Literal, Set, Tuple, Union

import strictyaml
from strictyaml import YAML

from recipemd.units import Quantity, UnitSystem


def load_quantity(name: str, yaml: YAML) -> Quantity:
    return Quantity.from_dict(yaml)

FQN = Tuple[str, ...]
FQNPredicate = Callable[[FQN], bool]

def add_key(value: Any, key):
    if isinstance(value, dict):
        value['id'] = key
    return value

def dicts_to_lists(data: Any, target_predicate: FQNPredicate, fqn: FQN = ()):
    if not isinstance(data, dict):
        return data

    if target_predicate(fqn):
        list_fqn = (*fqn, "[]")
        return [add_key(dicts_to_lists(value, target_predicate, list_fqn), key) for key, value in data.items()]

    return {key: dicts_to_lists(value, target_predicate, (*fqn, key)) for key, value in data.items()}

def merge_dicts(base: Any, diff: Any, merge_lists_predicate: FQNPredicate, fqn: FQN = ()):
    if isinstance(base, dict) and isinstance(diff, dict):   
        result = {}
        keys = {*base.keys(), *diff.keys()}
        for key in keys:
            base_present = key in base
            diff_present = key in diff
            if diff_present and diff[key] is None:
                pass
            elif base_present and diff_present:
                result[key] = merge_dicts(base[key], diff[key], merge_lists_predicate, (*fqn, key))
            elif diff_present:
                result[key] = diff[key]
            elif base_present:
                result[key] = base[key]
        return result

    if isinstance(base, list) and isinstance(diff, list) and merge_lists_predicate(fqn):
        return [*base, *diff]
    
    return diff
                
            


schema = strictyaml.Map({
    strictyaml.Optional("base"): strictyaml.Seq(
        strictyaml.Map({
            "path": strictyaml.Str(),
        })
    ),
    strictyaml.Optional("quantities"): strictyaml.MapPattern(
        strictyaml.Str(), 
        strictyaml.Map({
            strictyaml.Optional("base_unit"): strictyaml.Str(),
            strictyaml.Optional("units"):  strictyaml.MapPattern(
                strictyaml.Str(), 
                strictyaml.EmptyNone() | strictyaml.Map({
                    strictyaml.Optional("conversion_factor"): strictyaml.Decimal(),
                    strictyaml.Optional("alternative_names"): strictyaml.UniqueSeq(strictyaml.Str()),
                    strictyaml.Optional("display_ignore_max"): strictyaml.Decimal(),
                })
            ),
            strictyaml.Optional("display_units"): strictyaml.Seq(
                strictyaml.Map({
                    strictyaml.Optional("unit"): strictyaml.Str(),
                    strictyaml.Optional("min"): strictyaml.Decimal(),
                    strictyaml.Optional("max"): strictyaml.Decimal(),
                })
            )
        })
    )
})

if __name__ == '__main__':
    with open('recipemd/metric.yaml', 'r') as f:
        snippet = f.read()
    yaml_metric = strictyaml.load(snippet, schema=schema)
    # pprint(yaml_metric.data)

    with open('recipemd/metric_german.yaml', 'r') as f:
        snippet = f.read()
    yaml_metric_german = strictyaml.load(snippet, schema=schema)
    # pprint(yaml_metric_german.data)

    yaml = merge_dicts(
        yaml_metric.data, 
        yaml_metric_german.data, 
        lambda fqn: len(fqn) == 5 and fqn[0] == "quantities" and fqn[2] == "units" and fqn[4] == "names"
    )

    pprint(yaml)

    transformed = dicts_to_lists(yaml, lambda fqn: fqn in {("quantities",), ("quantities", "[]", "units")})
    pprint(transformed)
    pprint(UnitSystem.from_dict(transformed))
