from __future__ import annotations

import logging
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from langdetect import LangDetectException
from langdetect import detect as detect_language

import krawl.licenses as licenses
from krawl.file_formats import get_formats
from krawl.normalizer import Normalizer, strip_html
from krawl.project import File, Part, Project

log = logging.getLogger("wikifactory-normalizer")

# see https://soulaimanghanem.medium.com/github-repository-structure-best-practices-248e6effc405
EXCLUDE_FILES = [
    "ACKNOWLEDGMENTS",
    "AUTHORS",
    "CHANGELOG",
    "CODE_OF_CONDUCT",
    "CODEOWNERS",
    "CONTRIBUTING",
    "CONTRIBUTORS",
    "FUNDING",
    "ISSUE_TEMPLATE",
    "LICENSE",
    "PULL_REQUEST_TEMPLATE",
    "README",
    "SECURITY",
    "SUPPORT",
    "USERGUIDE",
    "USERMANUAL",
]
LICENSE_MAPPING = {
    "CC-BY-4.0": "CC-BY-4.0",
    "CC0-1.0": "CC0-1.0",
    "MIT": "MIT",
    "BSD-2-Clause": "BSD-2-Clause",
    "CC-BY-SA-4.0": "CC-BY-SA-4.0",
    "CC BY-SA": "CC-BY-SA-4.0",
    "GPL-3.0": "GPL-3.0-only",
    "OHL": "TAPR-OHL-1.0",
    "CERN OHL": "CERN-OHL-1.2",
    "CERN": "CERN-OHL-1.2",
    "alternativeLicense": "MIT"
}


# {
#     "oshwaUid": "SE000004",
#     "responsibleParty": "arturo182",
#     "country": "Sweden",
#     "publicContact": "oledpmod@solder.party",
#     "projectName": "0.95\" OLED PMOD",
#     "projectWebsite": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
#     "projectVersion": "1.0",
#     "projectDescription": "A tiny color OLED!\r\n\r\nPerfect solution if you need a small display with vivid, high-contrast 16-bit color. PMOD connector can be used with FPGA and MCU dev boards\r\n\r\nThe display itself is a 0.95&quot; color OLED, the resolution is 96x64 RGB pixels.\r\n\r\nThe display is driven by the SSD1331 IC, you can control it with a 4-wire write-only SPI. The board only supports 3.3V logic.",
#     "primaryType": "Other",
#     "additionalType": [
#         "Electronics"
#     ],
#     "projectKeywords": [
#         "oled",
#         "display",
#         "pmod"
#     ],
#     "citations": [],
#     "documentationUrl": "https://github.com/arturo182/pmod_rgb_oled_0.95in/",
#     "hardwareLicense": "CERN",
#     "softwareLicense": "No software",
#     "documentationLicense": "CC BY-SA",
#     "certificationDate": "2020-05-04T00:00-04:00"
# },
class OshwaNormalizer(Normalizer):

    def normalize(self, raw: dict) -> Project:

        project = Project()
        project.meta.source = raw["fetcher"]
        project.meta.host = raw["fetcher"]
        project.meta.owner = raw["responsibleParty"]
        project.meta.repo = self._normalize_repo(raw)
        project.meta.created_at = self._normalize_created_at(raw)  ## TODO can be not set
        project.meta.last_visited = raw["lastVisited"]

        log.debug("normalizing '%s'", project.id)
        project.name = raw["projectName"]
        project.repo = self._normalize_repo(raw)
        project.version = urllib.parse.quote(self._get_key(raw, 'projectVersion', default="0.1.0"))  ## todo can be none
        project.release = ""
        project.license = self._normalize_license(raw)
        project.licensor = raw['responsibleParty']
        # project.organization = self._normalize_organization(raw)
        # project.readme = self._get_info_file(["README"], files) ## TODO fetch readme from github???
        # project.contribution_guide = self._get_info_file(["CONTRIBUTING"], files)
        # project.image = self._normalize_image(raw)
        project.function = self._normalize_function(raw)
        project.documentation_language = self._normalize_language(project.function)
        project.technology_readiness_level = None
        project.documentation_readiness_level = None
        project.attestation = None
        project.publication = None
        project.standard_compliance = None
        project.cpc_patent_class = self._normalize_classification(raw) ## TODO where to add the cpc_classification
        project.tsdc = None
        project.bom = None
        project.manufacturing_instructions = None
        # project.user_manual = self._get_info_file(["USERGUIDE", "USERMANUAL"], files)
        project.outer_dimensions_mm = None
        # project.part = self._normalize_parts(files)
        project.software = []

        return project

    @staticmethod
    def _get_key(obj, *key, default=None):
        last = obj
        for k in key:
            if not last or k not in last:
                return default
            last = last[k]
        if not last:
            return default
        return last

    @classmethod
    def _normalize_created_at(cls, raw: dict):
        certification_date = raw.get("certificationDate")

        if not certification_date:
            return datetime.fromisoformat("1970-01-01 00:00:00")

        return datetime.fromisoformat(raw["certificationDate"])

    @classmethod
    def _normalize_classification(cls, raw: dict):
        primary_type = raw.get("primaryType")
        additional_type = raw.get("additionalType")

        unmappable_categories = [
            "Arts",
            "Education",
            "Environmental",
            "Manufacturing",
            "Other",
            "Science",
            "Tool"
        ]

        if primary_type in unmappable_categories:
            if additional_type is None:
                return ""
            if len(additional_type) == 0:
                return ""
            else:
                return additional_type

        mapping_primary_to_cpc = {
            "3D Printing": "B33Y",
            "Agriculture": "A01",
            "Electronics": "H",
            "Enclosure": "F16M",
            "Home Connection": "H04W",
            "IOT": "H04",
            "Robotics": "B25J9 / 00",
            "Sound": "H04R",
            "Space": "B64G",
            "Wearables": "H"
        }

        try:
            cpc = mapping_primary_to_cpc[primary_type]
            return cpc
        except KeyError:
            return primary_type

    @classmethod
    def _normalize_organization(cls, raw: dict):
        parent_type = raw["parentContent"]["type"]
        if parent_type == "initiative":
            return raw["parentContent"]["title"]
        return None

    @classmethod
    def _normalize_license(cls, raw: dict):
        raw_license = cls._get_key(raw, "hardwareLicense")

        ## TODO clear this with moe

        if not raw_license:
            return None

        if raw_license == "None" or raw_license == "Other":
            return None

        return licenses.get_by_id_or_name(LICENSE_MAPPING.get(raw_license))

    @classmethod
    def _normalize_function(cls, raw: dict):
        raw_description = raw.get("projectDescription")
        if not raw_description:
            return ""
        description = strip_html(raw_description).strip()
        return description

    @classmethod
    def _normalize_language(cls, description: str):
        if not description:
            return "en"
        try:
            lang = detect_language(description)
        except LangDetectException:
            return "en"
        if lang == "unknown":
            return "en"
        return lang

    @classmethod
    def _normalize_repo(cls, raw: dict):
        doc_url = raw.get('documentationUrl')

        ## TODO can be none

        if not doc_url:
            return f"https://certification.oshwa.org/{raw['oshwaUid']}.html"

        return doc_url

    @classmethod
    def _parse_file(cls, file_raw: dict) -> File:
        file = File()
        file.path = Path(file_raw["filename"]) if "filename" in file_raw else None
        file.name = file.path.stem if file.path else None
        file.mime_type = file_raw.get("mimeType", None)
        file.url = file_raw.get("url", None)
        file.perma_url = file_raw.get("permalink", None)
        file.created_at = datetime.strptime(file_raw["dateCreated"], "%Y-%m-%dT%H:%M:%S.%f%z")
        file.last_changed = datetime.strptime(file_raw["lastUpdated"], "%Y-%m-%dT%H:%M:%S.%f%z")
        file.last_visited = datetime.now(timezone.utc)
        file.license = file_raw["license"]
        file.licensor = cls._get_key(file_raw, "creator", "profile", "fullName")
        return file

    @classmethod
    def _get_files(cls, raw: dict) -> list[File]:
        raw_files = cls._get_key(raw, "contribution", "files", default=[])
        files = []
        license = cls._normalize_license(raw)
        for meta in raw_files:
            file_raw = meta.get("file")
            if not file_raw:
                continue
            dir_name = meta["dirname"]
            if dir_name:
                file_raw["path"] = f"{dir_name}/{file_raw['filename']}"
            file_raw["license"] = license
            file = cls._parse_file(file_raw)
            if file:
                files.append(file)

        return files

    @classmethod
    def _normalize_parts(cls, files: list[File]) -> list[Part]:
        # filter out readme and other files
        filtered = []
        for file in files:
            normalized_name = file.path.stem.replace(" ", "_").replace("-", "_").upper()
            if normalized_name in EXCLUDE_FILES:
                continue
            filtered.append(file)

        # put files in buckets
        buckets = defaultdict(list)
        for file in filtered:
            normalized_name = str(file.path.with_suffix("")).lower()
            buckets[normalized_name].append(file)

        # figure out what files are the sources, the exports and the images
        cad_formats = get_formats("cad")
        pcb_formats = get_formats("pcb")
        image_formats = get_formats("image")
        parts = []
        for fl in buckets.values():
            part = Part()
            for file in fl:
                ext = "." + file.extension

                # get sources and exports by extension
                if ext in cad_formats:
                    format_ = cad_formats[ext]
                    if format_.category == "source":
                        if not part.source:
                            part.source = file
                        else:
                            part.export.append(file)
                    elif format_.category == "export":
                        part.export.append(file)
                    continue
                if ext in pcb_formats:
                    format_ = pcb_formats[ext]
                    if format_.category == "source":
                        if not part.source:
                            part.source = file
                        else:
                            part.export.append(file)
                    elif format_.category == "export":
                        part.export.append(file)
                    continue

                # get first image by extension
                if ext in image_formats:
                    format_ = image_formats[ext]
                    if not part.image:
                        part.image = file
                    continue

            # if no sources are identified, but exports, then use the exportsinstead
            if not part.source and part.export:
                part.source = part.export.pop(0)

            # only add, if a source file was identified
            if part.source:
                part.name = part.source.name
                part.license = part.source.license
                part.licensor = part.source.licensor
                parts.append(part)

        return parts

    @classmethod
    def _normalize_image(cls, raw: dict) -> File:
        image_raw = raw.get("image", {})
        if not image_raw:
            return None
        return cls._parse_file(image_raw)

    @classmethod
    def _get_info_file(cls, names, files) -> File:
        for file in files:
            # only consider files in root dir
            if len(file.path.parents) > 1:
                continue
            if file.path.stem.strip().replace(" ", "").replace("-", "").replace("_", "").upper() in names:
                return file
        return None