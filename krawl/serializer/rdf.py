from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import rdflib
import validators

from krawl.namespaces import OKH, OTLR
from krawl.project import Project
from krawl.serializer import ProjectSerializer

# Useful info about RDF:
# https://medium.com/wallscope/understanding-linked-data-formats-rdf-xml-vs-turtle-vs-n-triples-eb931dbe9827


class RDFProjectSerializer(ProjectSerializer):

    def serialize(self, project: Project) -> str:
        graph = self._make_graph(project)
        return graph.serialize(format="turtle").decode("utf-8")

    def deserialize(self, serialized: str) -> Project:
        raise NotImplementedError()

    @staticmethod
    def _make_project_namespace(project) -> rdflib.Namespace:
        parts = urlparse(project.repo)
        base = urlunparse(components=(
            parts.scheme,
            parts.netloc,
            str(Path(parts.path, project.version)) + "/",
            "",
            "",
            "",
        ))
        return rdflib.Namespace(base)

    @staticmethod
    def _make_OTRL(project):
        v = project.technology_readiness_level
        if v is None:
            return None
        return getattr(OTLR, v)

    @staticmethod
    def _titlecase(s):
        parts = s.split(" ")
        capitalized = "".join([p.capitalize() for p in parts])
        alphanum = "".join([l for l in capitalized if l.isalnum()])
        return alphanum

    @staticmethod
    def _camelcase(s):
        parts = s.split("-")
        withoutdash = "".join([parts[0]] + [p.capitalize() for p in parts[1:]])
        return withoutdash

    @staticmethod
    def add(graph: rdflib.Graph, subject, predicate, object):
        if object is not None:
            if isinstance(object, str) and validators.url(object):
                object = rdflib.URIRef(object)
            elif isinstance(object, datetime):
                object = rdflib.Literal(object.isoformat())
            elif not isinstance(object, (rdflib.URIRef, rdflib.Literal)):
                object = rdflib.Literal(object)
            graph.add((subject, predicate, object))

    @classmethod
    def add_file(cls, graph, subject, file):
        cls.add(graph, subject, OKH.fileUrl, file.url)
        cls.add(graph, subject, OKH.permaURL, file.perma_url)
        cls.add(graph, subject, OKH.fileFormat, file.extension.upper())
        # cls.add(graph, subject, OKH.mimeType, file.mime_type) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateCreated, file.created_at) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastChanged, file.last_changed) # FIXME: only add if contained in ontology
        # cls.add(graph, subject, OKH.dateLastVisited, file.last_visited) # FIXME: only add if contained in ontology

    @classmethod
    def _add_part(cls, graph, namespace, project) -> rdflib.URIRef:

        def get_fallback(part, key):
            if hasattr(part, key):
                return getattr(part, key)
            return getattr(project, key)

        part_subjects = []
        for part in project.part:
            partname = cls._titlecase(part.name if part.name != project.name else part.name + "_part")

            part_subject = namespace[partname]
            cls.add(graph, part_subject, rdflib.RDF.type, OKH.Part)
            cls.add(graph, part_subject, rdflib.RDFS.label, part.name)

            cls.add(graph, part_subject, OKH.documentationLanguage, get_fallback(part, "documentation_language"))
            license = get_fallback(part, "license")
            if license and license.is_spdx:
                cls.add(graph, part_subject, OKH.spdxLicense, license)
            else:
                cls.add(graph, part_subject, OKH.alternativeLicense, license)
            cls.add(graph, part_subject, OKH.licensor, get_fallback(part, "licensor"))
            cls.add(graph, part_subject, OKH.material, part.material)
            cls.add(graph, part_subject, OKH.manufacturingProcess, part.manufacturing_process)
            cls.add(graph, part_subject, OKH.outerDimensionsMM, part.outer_dimensions_mm)
            cls.add(graph, part_subject, OKH.tsdc, part.tsdc)

            # source
            if part.source is not None:
                source_subject = namespace[f"{partname}_source"]
                cls.add(graph, part_subject, OKH.source, source_subject)
                cls.add(graph, source_subject, rdflib.RDF.type, OKH.SourceFile)
                cls.add(graph, source_subject, rdflib.RDFS.label,
                        f"Source File of {part.name} of {project.name} v{project.version}")
                cls.add_file(graph, source_subject, part.source)

            # export
            for i, file in enumerate(part.export):
                export_subject = namespace[f"{partname}_export{i+1}"]
                cls.add(graph, part_subject, OKH.export, export_subject)
                cls.add(graph, export_subject, rdflib.RDF.type, OKH.ExportFile)
                cls.add(graph, export_subject, rdflib.RDFS.label,
                        f"Export File of {part.name} of {project.name} v{project.version}")
                cls.add_file(graph, export_subject, file)

            # image
            if part.image is not None:
                image_subject = namespace[f"{partname}_image"]
                cls.add(graph, part_subject, OKH.image, image_subject)
                cls.add(graph, image_subject, rdflib.RDF.type, OKH.Image)
                cls.add(graph, image_subject, rdflib.RDFS.label,
                        f"Image of {part.name} of {project.name} v{project.version}")
                cls.add_file(graph, image_subject, part.image)

            part_subjects.append(part_subject)

        return part_subjects

    @classmethod
    def _add_module(cls, graph, namespace, project) -> rdflib.URIRef:
        module_subject = namespace[cls._titlecase(project.name)]
        cls.add(graph, module_subject, rdflib.RDF.type, OKH.Module)

        cls.add(graph, module_subject, rdflib.RDFS.label, project.name)
        cls.add(graph, module_subject, OKH.versionOf, project.repo)
        cls.add(graph, module_subject, OKH.repo, project.repo)
        cls.add(graph, module_subject, OKH.dataSource, project.meta.source)
        cls.add(graph, module_subject, OKH.repoHost, project.meta.host)
        cls.add(graph, module_subject, OKH.version, project.version)
        cls.add(graph, module_subject, OKH.release,
                None)  # TODO look for 'release' in toml or if missing, check for latest github release
        if project.license.is_spdx:
            cls.add(graph, module_subject, OKH.spdxLicense, project.license)
        else:
            cls.add(graph, module_subject, OKH.alternativeLicense, project.license)
        cls.add(graph, module_subject, OKH.licensor, project.licensor)
        cls.add(graph, module_subject, OKH.organization, project.organization)
        # cls.add(graph, module_subject, OKH.contributorCount, None)  ## TODO see if github api can do this

        # graph, add(OKH.timestamp, project.timestamp)
        cls.add(graph, module_subject, OKH.documentationLanguage, project.documentation_language)
        # cls.add(graph, module_subject, OKH.technologyReadinessLevel, cls._make_OTRL(project))
        cls.add(graph, module_subject, OKH.function, project.function)
        cls.add(graph, module_subject, OKH.cpcPatentClass, project.cpc_patent_class)
        cls.add(graph, module_subject, OKH.tsdc, project.tsdc)

        cls.add(graph, module_subject, OKH.outerDimensionMM, project.outer_dimensions_mm)

        return module_subject

    # def _make_functional_metadata_list(self, module, functional_metadata, BASE):
    #     l = []
    #     for key, value in functional_metadata.items():
    #         keyC = self._camelcase(key)
    #         l.append((module, BASE[keyC], rdflib.Literal(value)))
    #         entity = BASE[keyC]
    #         l.append((entity, rdflib.RDF.type, rdflib.OWL.DatatypeProperty))
    #         l.append((entity, rdflib.RDFS.label, rdflib.Literal(key)))
    #         l.append((entity, rdflib.RDFS.subPropertyOf, OKH.functionalMetadata))
    #     return l

    # def _make_file_list(self, project, key, entityname, rdftype, BASE, extra=None):
    #     extra = [] if extra is None else extra
    #     parentname = f"{project.name} v{project.version}"
    #     l = []
    #     value = getattr(project, detailskey(key)) if hasattr(project, detailskey(key)) else None
    #     if value is None:
    #         return None
    #     entity = BASE[entityname]
    #     l.append((entity, rdflib.RDF.type, rdftype))
    #     l.append((entity, rdflib.RDFS.label, f"{entityname} of {parentname}"))
    #     for a, v in extra:
    #         l.append((entity, a, v))
    #     for k, v in value.items():
    #         l.append((entity, getattr(OKH, k), v))
    #     return entity, l

    @classmethod
    def _add_info_file(cls, graph, namespace, project, key, entityname, rdftype):
        parentname = f"{project.name} v{project.version}"
        file = getattr(project, key) if hasattr(project, key) else None
        if file is None:
            return None

        subject = namespace[entityname]
        cls.add(graph, subject, rdflib.RDF.type, rdftype)
        cls.add(graph, subject, rdflib.RDFS.label, f"{entityname} of {parentname}")
        cls.add_file(graph, subject, file)
        return subject

    @classmethod
    def _make_graph(cls, project):
        graph = rdflib.Graph()
        graph.bind("okh", OKH)
        graph.bind("rdfs", rdflib.RDFS)
        graph.bind("owl", rdflib.OWL)
        graph.bind("otlr", OTLR)

        namespace = cls._make_project_namespace(project)
        graph.bind("", namespace)

        module_subject = cls._add_module(graph, namespace, project)

        readme_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="readme",
            entityname=f"Readme",
            rdftype=OKH.Readme,
        )
        if readme_subject is not None:
            cls.add(graph, module_subject, OKH.hasReadme, readme_subject)

        manifest_file_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manifest_file",
            entityname="ManifestFile",
            rdftype=OKH.ManifestFile,
        )
        if manifest_file_subject is not None:
            cls.add(graph, manifest_file_subject, OKH.okhv, project.okhv)
            cls.add(graph, module_subject, OKH.hasBoM, manifest_file_subject)

        image_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="image",
            entityname="Image",
            rdftype=OKH.Image,
        )
        if image_subject is not None:
            cls.add(graph, module_subject, OKH.hasImage, image_subject)

        bom_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="bom",
            entityname="Bill of Materials",
            rdftype=OKH.BoM,
        )
        if bom_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, bom_subject)

        manufacturing_instructions_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="manufacturing_instructions",
            entityname="ManufacturingInstructions",
            rdftype=OKH.ManufacturingInstructions,
        )
        if manufacturing_instructions_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, manufacturing_instructions_subject)

        user_manual_subject = cls._add_info_file(
            graph=graph,
            namespace=namespace,
            project=project,
            key="user_manual",
            entityname="UserManual",
            rdftype=OKH.UserManual,
        )
        if user_manual_subject is not None:
            cls.add(graph, module_subject, OKH.hasBoM, user_manual_subject)

        part_subjects = cls._add_part(graph, namespace, project)
        for part_subject in part_subjects:
            cls.add(graph, module_subject, OKH.hasComponent, part_subject)

        return graph

    @staticmethod
    def _extend(l, v):
        if v is not None:
            l.extend(v)