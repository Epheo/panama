#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2014 Thibaut Lapierre <git@epheo.eu>. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from jinja2 import Template
import os.path
import yaml


class ModelDefinition(object):
    """Container definition

    This class is loading the model from the yaml files and provides
    different methods to read from it more easily.
    """

    def __init__(self, app_args):
        self.app_args = app_args
        self.cluster_name = app_args.shdk_cluster

        Loader.add_constructor('!include', Loader.include)

        if app_args.shdk_model is None:
            raise NameError("You should specify a template file with -f")
        with open(app_args.shdk_model) as f:
            self.model = yaml.load(f, Loader)

    def _get_clusters_list(self):
        """Return a cluster list from the model.

        This method  return the differents clusters as a list of dicts.
        """

        cluster_list = []
        for cluster in self.model['clusters']:
            cluster['services'] = str(cluster['services'])
            cluster_list.append(cluster)
        return cluster_list

    def _get_cluster(self, name):
        cluster_list = self._get_clusters_list()
        try:
            cluster = [clu for clu in cluster_list if
                       clu['name'] == name]
            if len(cluster) > 1:
                raise TemplateFileError(
                    "There is more than one definition matching"
                    " 'name: {}' in your model".format(name))
            cluster = cluster[0]
        except IndexError:
            raise TemplateFileError(
                "There is no cluster definition containing"
                " 'name: {}' in your model".format(name))
        except KeyError:
            raise TemplateFileError(
                "At least one cluster definition "
                "is missing the name property")
        return cluster

    def _get_services_list_from_clu(self, cluster):
        """Return a list of services
        """

        services_list = []
        if 'vars' in cluster:
            j2 = Template(cluster['services'])
            services_yaml = j2.render(cluster['vars'])
            services = yaml.load(services_yaml)
        else:
            services = yaml.load(cluster['services'])
        cluster['services'] = services

        for service in cluster['services']:
            service['cluster_name'] = cluster['name']
            service['cluster'] = cluster
            services_list.append(service)
        return services_list

    def get_services_list(self):
        """This method returns a service as a dict.
        """
        if self.cluster_name is None:
            cluster_list = self._get_clusters_list()
            svc_list = []
            for clu in cluster_list:
                clu_svc_list = self._get_services_list_from_clu(clu)
                svc_list = svc_list + clu_svc_list
        else:
            cluster = self._get_cluster(self.cluster_name)
            svc_list = self._get_services_list_from_clu(cluster)
        return svc_list

    def get_service(self, name):
        """This method returns a service as a dict.
        """
        services_list = self.get_services_list()

        try:
            service = [svc for svc in services_list if
                       svc['name'] == name]
            if len(service) > 1:
                raise TemplateFileError(
                    "There is more than one definition matching"
                    " 'name: {}' in your model".format(name))
            service = service[0]
        except IndexError:
            raise TemplateFileError(
                "There is no container definition containing"
                " 'name: {}' in your model".format(name))
        except KeyError:
            raise TemplateFileError(
                "At least one container definition in your model"
                " is missing the name property")

        # Image dir definition:
        #
        if self.app_args.shdk_imgdir is not None:
            service['images_dir'] = self.app_args.shdk_imgdir
        else:
            try:
                service['images_dir'] = os.path.join(
                    os.path.dirname(self.app_args.shdk_model),
                    service['cluster']['images'])
            except TypeError:
                raise TemplateFileError(
                    "Cluster definition in your model is missing the images"
                    " key. "
                    "If you don't want to define a static images path in "
                    "your model you can also specify a directory to build "
                    "in with the -d cli arg.")
        try:
            service['image']
        except KeyError:
            raise TemplateFileError(
                "Container definition of: '{}' in your model is"
                " missing the image property".format(name))

        service['path'] = '{}/{}'.format(service['images_dir'],
                                         service['image'].split(":")[0])

        # Networking definition:
        #

        port_bindings = service.get('ports')
        if port_bindings is not None:
            service['ports'] = [item for item in port_bindings.keys()]
            service['port_bindings'] = port_bindings

        # Volume definition:
        #
        binds = service.get('volumes')
        if binds is not None:
            service['volumes'] = [item for item in binds.keys()]
            service['binds'] = binds

        # Host API Definition:
        #
        api_cfg = {}
        if self.app_args.docker_url is not None:
            api_cfg['url'] = self.app_args.docker_url
            api_cfg['version'] = self.app_args.docker_version
            api_cfg['cert_path'] = self.app_args.docker_cert_path
            api_cfg['key_path'] = self.app_args.docker_key_path
            api_cfg['cacert_path'] = self.app_args.docker_cacert_path
            api_cfg['tls_verify'] = self.app_args.docker_tls_verify
            api_cfg['tls'] = self.app_args.docker_tls
            api_cfg['boot2docker'] = self.app_args.docker_boot2docker
        else:
            try:
                api_cfg = [api for api in service['cluster']['hosts'] if
                           api['name'] == service['host']]
                if len(api_cfg) > 1:
                    raise TemplateFileError(
                        "There is more than one definition matching"
                        " 'name: {}' in your model".format(name))
                api_cfg = api_cfg[0]
            except KeyError:
                pass
            except IndexError:
                raise TemplateFileError(
                    "There is no Docker Host definition containing"
                    " 'name: {}' in your model.".format(service['host']))
        service['api_cfg'] = api_cfg
        return service


class TemplateFileError(Exception):
    pass


class Loader(yaml.Loader):
    """Include

    This class change the Yaml Load fct to allow file inclusion
    using the !include keywork.
    """
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        try:
            with open(filename, 'r') as f:
                return yaml.load(f, Loader)
        except Exception:
            raise TemplateFileError(
                "The file {} you're trying to include doesn't"
                "exist.".format(filename))
