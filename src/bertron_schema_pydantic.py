from __future__ import annotations

import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


metamodel_version = "None"
version = "0.0.2"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
        strict=False,
    )
    pass


class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key: str):
        return getattr(self.root, key)

    def __getitem__(self, key: str):
        return self.root[key]

    def __setitem__(self, key: str, value):
        self.root[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta(
    {
        "default_curi_maps": ["semweb_context"],
        "default_prefix": "bertron",
        "default_range": "string",
        "description": "Schema for BERtron common data model.",
        "id": "https://w3id.org/ber-data/bertron-schema",
        "imports": ["linkml:types", "bertron_types"],
        "license": "BSD-3",
        "name": "bertron-schema",
        "prefixes": {
            "MIXS": {
                "prefix_prefix": "MIXS",
                "prefix_reference": "https://w3id.org/mixs/",
            },
            "UO": {
                "prefix_prefix": "UO",
                "prefix_reference": "http://purl.obolibrary.org/obo/UO_",
            },
            "WGS84": {
                "prefix_prefix": "WGS84",
                "prefix_reference": "http://www.w3.org/2003/01/geo/wgs84_pos#",
            },
            "bertron": {
                "prefix_prefix": "bertron",
                "prefix_reference": "https://w3id.org/ber-data/bertron-schema/",
            },
            "linkml": {
                "prefix_prefix": "linkml",
                "prefix_reference": "https://w3id.org/linkml/",
            },
            "schema": {
                "prefix_prefix": "schema",
                "prefix_reference": "http://schema.org/",
            },
        },
        "see_also": ["https://ber-data.github.io/bertron-schema"],
        "source_file": "src/schema/linkml/bertron_schema.yaml",
        "title": "BERtron schema",
    }
)


class BERSourceType(str, Enum):
    """
    The BER data source from whence the entity originated.
    """

    EMSL = "EMSL"
    ESS_DIVE = "ESS-DIVE"
    JGI = "JGI"
    MONET = "MONET"
    NMDC = "NMDC"


class EntityType(str, Enum):
    """
    Tags used to describe an entity.
    """

    biodata = "biodata"
    jgi_biosample = "jgi_biosample"
    sample = "sample"
    sequence = "sequence"
    taxon = "taxon"
    unspecified = "unspecified"


class NameType(str, Enum):
    """
    The relationship between a name and a synonym of that name.
    """

    broad_synonym = "broad_synonym"
    """
    The synonym refers to a broader group of entities than the name.
    """
    exact_synonym = "exact_synonym"
    """
    String with exactly the same meaning and connotations as the original name.
    """
    narrow_synonym = "narrow_synonym"
    """
    The synonym refers to a narrower group of entities than the name.
    """
    related_synonym = "related_synonym"
    """
    The synonym has overlap with the name but the precise relationship is not defined.
    """
    acronym = "acronym"
    """
    An acronym or abbreviation for the name.
    """


class AttributeValue(ConfiguredBaseModel):
    """
    The value for any value of a attribute for a sample. This object can hold both the un-normalized atomic value and the structured value
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "abstract": True,
            "class_uri": "nmdc:AttributeValue",
            "from_schema": "https://w3id.org/ber-data/bertron_types",
        }
    )

    has_raw_value: Optional[str] = Field(
        default=None,
        description="""The value that was specified for an annotation in raw form, i.e. a string. E.g. \"2 cm\" or \"2-4 cm\"""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_raw_value",
                "domain_of": ["AttributeValue", "QuantityValue"],
                "mappings": ["nmdc:has_raw_value"],
            }
        },
    )


class QuantityValue(AttributeValue):
    """
    A simple quantity, e.g. 2cm
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "nmdc:QuantityValue",
            "from_schema": "https://w3id.org/ber-data/bertron_types",
            "mappings": ["schema:QuantityValue"],
            "slot_usage": {
                "has_numeric_value": {
                    "description": "The number part of the quantity",
                    "name": "has_numeric_value",
                },
                "has_raw_value": {
                    "description": "Unnormalized atomic string "
                    "representation, should in "
                    "syntax {number} {unit}",
                    "name": "has_raw_value",
                },
                "has_unit": {
                    "description": "The unit of the quantity",
                    "name": "has_unit",
                },
            },
        }
    )

    has_maximum_numeric_value: Optional[float] = Field(
        default=None,
        description="""The maximum value part, expressed as number, of the quantity value when the value covers a range.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_maximum_numeric_value",
                "domain_of": ["QuantityValue"],
                "is_a": "has_numeric_value",
                "mappings": ["nmdc:has_maximum_numeric_value"],
            }
        },
    )
    has_minimum_numeric_value: Optional[float] = Field(
        default=None,
        description="""The minimum value part, expressed as number, of the quantity value when the value covers a range.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_minimum_numeric_value",
                "domain_of": ["QuantityValue"],
                "is_a": "has_numeric_value",
                "mappings": ["nmdc:has_minimum_numeric_value"],
            }
        },
    )
    has_numeric_value: Optional[float] = Field(
        default=None,
        description="""The number part of the quantity""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_numeric_value",
                "domain_of": ["QuantityValue"],
                "mappings": [
                    "nmdc:has_numeric_value",
                    "qud:quantityValue",
                    "schema:value",
                ],
            }
        },
    )
    has_raw_value: Optional[str] = Field(
        default=None,
        description="""Unnormalized atomic string representation, should in syntax {number} {unit}""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_raw_value",
                "domain_of": ["AttributeValue", "QuantityValue"],
                "mappings": ["nmdc:has_raw_value"],
            }
        },
    )
    has_unit: Optional[str] = Field(
        default=None,
        description="""The unit of the quantity""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "has_unit",
                "aliases": ["scale"],
                "domain_of": ["QuantityValue"],
                "mappings": ["nmdc:has_unit", "qud:unit", "schema:unitCode"],
            }
        },
    )


class Entity(ConfiguredBaseModel):
    """
    An object retrieved by BERtron from a BER data API.

    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "schema:Thing",
            "from_schema": "https://w3id.org/ber-data/bertron-schema",
        }
    )

    ber_data_source: BERSourceType = Field(
        default=...,
        description="""The BER member from whence the entity originated.""",
        json_schema_extra={
            "linkml_meta": {"alias": "ber_data_source", "domain_of": ["Entity"]}
        },
    )
    coordinates: Coordinates = Field(
        default=...,
        description="""The geographic coordinates associated with an entity. For entities with a bounding box, the centroid is used as the geographic reference.""",
        json_schema_extra={
            "linkml_meta": {"alias": "coordinates", "domain_of": ["Entity"]}
        },
    )
    entity_type: list[EntityType] = Field(
        default=...,
        description="""What kind of entity is this -- e.g. sequence data; a soil core; a well; field site; sample; etc.""",
        json_schema_extra={
            "linkml_meta": {"alias": "entity_type", "domain_of": ["Entity"]}
        },
    )
    description: Optional[str] = Field(
        default=None,
        description="""Textual description of the entity.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "description",
                "domain_of": ["Entity", "DataCollection"],
                "examples": [
                    {"value": "River water sample taken by AquaTROLL 9000."},
                    {"value": "Genome sequence of P. aeruginosa strain IDDQD"},
                ],
                "slot_uri": "schema:description",
            }
        },
    )
    id: Optional[str] = Field(
        default=None,
        description="""The unique ID used for the entity within the BER resource. It may not necessarily be resolvable outside the resource.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "id",
                "aliases": ["BER data source internal identifier", "CURIE"],
                "comments": [
                    "If the data source does not use CURIEs, we cannot guarantee "
                    "that IDs will be unique between all the BER sources."
                ],
                "domain_of": ["Entity", "DataCollection"],
                "slot_uri": "schema:identifier",
            }
        },
    )
    name: Optional[str] = Field(
        default=None,
        description="""Human-readable string representing an entity.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "name",
                "domain_of": ["Entity", "Name"],
                "examples": [
                    {"value": "Pseudomonas aeruginosa strain IDDQD"},
                    {"value": "Soil core FW-106"},
                ],
                "slot_uri": "schema:name",
            }
        },
    )
    alt_ids: Optional[list[str]] = Field(
        default=None,
        description="""Fully-qualified URI or CURIE used as an identifier for an entity.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "alt_ids",
                "aliases": [
                    "CURIEs",
                    "database cross-references",
                    "dbxrefs",
                    "IDs",
                    "alternative identifiers",
                    "alternative IDs",
                    "alternative PIDs",
                    "PIDs",
                ],
                "comments": ["The entity `id` should not appear in this list."],
                "domain_of": ["Entity", "DataCollection"],
                "examples": [
                    {"value": "NCBItaxon:172684329"},
                    {"value": "ISGN:1986497"},
                ],
            }
        },
    )
    alt_names: Optional[list[Name]] = Field(
        default=None,
        description="""Textual identifiers for an entity.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "alt_names",
                "aliases": ["alternative names", "synonyms"],
                "comments": ["The entity `name` should not appear in this list."],
                "domain_of": ["Entity"],
            }
        },
    )
    part_of_collection: Optional[list[DataCollection]] = Field(
        default=None,
        description="""Administrative collection (e.g. project, campaign, whatever) that the entity was generated as part of. May also be called a project.""",
        json_schema_extra={
            "linkml_meta": {"alias": "part_of_collection", "domain_of": ["Entity"]}
        },
    )
    uri: str = Field(
        default=...,
        description="""Permanent resolvable URI for the entity at the data source.""",
        json_schema_extra={
            "linkml_meta": {"alias": "uri", "aliases": ["url"], "domain_of": ["Entity"]}
        },
    )


class Coordinates(ConfiguredBaseModel):
    """
    The coordinates defining the position associated with the entity.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/ber-data/bertron-schema"}
    )

    altitude: Optional[QuantityValue] = Field(
        default=None,
        title="altitude",
        description="""Altitude is a term used to identify heights of objects such as airplanes, space shuttles, rockets, atmospheric balloons and heights of places such as atmospheric layers and clouds. It is used to measure the height of an object which is above the earth's surface. In this context, the altitude measurement is the vertical distance between the earth's surface above sea level and the sampled position in the air""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "altitude",
                "annotations": {
                    "expected_value": {
                        "tag": "expected_value",
                        "value": "measurement value",
                    }
                },
                "domain_of": ["Coordinates"],
                "examples": [{"value": "100 meter"}],
                "slot_uri": "MIXS:0000094",
            }
        },
    )
    depth: Optional[QuantityValue] = Field(
        default=None,
        title="depth",
        description="""The vertical distance below local surface, e.g. for sediment or soil samples depth is measured from sediment or soil surface, respectively. Depth can be reported as an interval for subsurface samples.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "depth",
                "aliases": ["depth"],
                "annotations": {
                    "expected_value": {
                        "tag": "expected_value",
                        "value": "measurement value",
                    }
                },
                "domain_of": ["Coordinates"],
                "examples": [{"value": "10 meter"}],
                "slot_uri": "MIXS:0000018",
            }
        },
    )
    elevation: Optional[QuantityValue] = Field(
        default=None,
        title="elevation",
        description="""Elevation of the sampling site is its height above a fixed reference point, most commonly the mean sea level. Elevation is mainly used when referring to points on the earth's surface, while altitude is used for points above the surface, such as an aircraft in flight or a spacecraft in orbit.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "elevation",
                "aliases": ["elevation"],
                "annotations": {
                    "expected_value": {
                        "tag": "expected_value",
                        "value": "measurement value",
                    }
                },
                "domain_of": ["Coordinates"],
                "examples": [{"value": "100 meter"}],
                "slot_uri": "MIXS:0000093",
            }
        },
    )
    latitude: float = Field(
        default=...,
        description="""latitude""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "latitude",
                "broad_mappings": ["MIXS:0000009"],
                "domain_of": ["Coordinates"],
                "examples": [{"value": "-33.460524"}],
                "mappings": ["schema:latitude"],
                "slot_uri": "WGS84:lat",
            }
        },
    )
    longitude: float = Field(
        default=...,
        description="""longitude""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "longitude",
                "broad_mappings": ["MIXS:0000009"],
                "domain_of": ["Coordinates"],
                "examples": [{"value": "150.168149"}],
                "mappings": ["schema:longitude"],
                "slot_uri": "WGS84:long",
            }
        },
    )


class Name(ConfiguredBaseModel):
    """
    The name or label for an entity. This may be a primary name, alternative name, synonym, acronym, or any other label used to refer to an entity.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/ber-data/bertron-schema"}
    )

    name_type: Optional[NameType] = Field(
        default=None,
        description="""Brief description of the name and/or its relationship to the entity.""",
        json_schema_extra={
            "linkml_meta": {"alias": "name_type", "domain_of": ["Name"]}
        },
    )
    name: str = Field(
        default=...,
        description="""The string used as a name.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "name",
                "domain_of": ["Entity", "Name"],
                "examples": [
                    {"value": "Heat-inducible transcription repressor HrcA"},
                    {"value": "FW106 groundwater metagenome"},
                ],
                "slot_uri": "schema:name",
            }
        },
    )


class DataCollection(ConfiguredBaseModel):
    """
    Administrative unit (e.g. project, proposal, etc.) in which one or more entities is collected.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "comments": [
                "May be equivalent to FundingReference in the CreditMetadata schema."
            ],
            "from_schema": "https://w3id.org/ber-data/bertron-schema",
        }
    )

    id: Optional[str] = Field(
        default=None,
        description="""The unique ID used for the project within the BER resource. It may not necessarily be resolvable outside the resource.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "id",
                "aliases": ["proposal ID", "project ID"],
                "comments": [
                    "If the data source does not use CURIEs, we cannot guarantee "
                    "that IDs will be unique between all the BER sources."
                ],
                "domain_of": ["Entity", "DataCollection"],
                "slot_uri": "schema:identifier",
            }
        },
    )
    title: Optional[str] = Field(
        default=None,
        description="""Human-readable string representing the project.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "title",
                "aliases": ["name"],
                "domain_of": ["DataCollection"],
                "slot_uri": "schema:name",
            }
        },
    )
    description: Optional[str] = Field(
        default=None,
        description="""Textual description of the project.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "description",
                "domain_of": ["Entity", "DataCollection"],
                "slot_uri": "schema:description",
            }
        },
    )
    alt_ids: Optional[list[str]] = Field(
        default=None,
        description="""Fully-qualified URI or CURIE used as an identifier for a project.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "alt_ids",
                "aliases": [
                    "CURIEs",
                    "database cross-references",
                    "dbxrefs",
                    "IDs",
                    "alternative identifiers",
                    "alternative IDs",
                    "alternative PIDs",
                    "PIDs",
                ],
                "comments": ["The project `id` should not appear in this list."],
                "domain_of": ["Entity", "DataCollection"],
            }
        },
    )
    alt_titles: Optional[list[Name]] = Field(
        default=None,
        description="""Alternative versions of the title/name of a project.""",
        json_schema_extra={
            "linkml_meta": {
                "alias": "alt_titles",
                "aliases": ["alternative titles"],
                "comments": ["The project `title` should not appear in this list."],
                "domain_of": ["DataCollection"],
            }
        },
    )
    url: str = Field(
        default=...,
        description="""Permanent resolvable URI for the collection at the data source.""",
        json_schema_extra={
            "linkml_meta": {"alias": "url", "domain_of": ["DataCollection"]}
        },
    )


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
AttributeValue.model_rebuild()
QuantityValue.model_rebuild()
Entity.model_rebuild()
Coordinates.model_rebuild()
Name.model_rebuild()
DataCollection.model_rebuild()
