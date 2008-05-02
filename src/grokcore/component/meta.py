#############################################################################
#
# Copyright (c) 2006-2007 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Grokkers for the various components."""

import martian.util
import grokcore.component
import zope.component.interface

from zope import component, interface
from martian.error import GrokError
from grokcore.component.util import check_adapts
from grokcore.component.util import check_module_component
from grokcore.component.util import determine_module_component
from grokcore.component.util import check_provides_one
from grokcore.component import directive

def get_context(factory, module_info):
    component = directive.context.get(factory, module_info.getModule())
    check_module_component(factory, component, 'context', directive.context)
    return component

def get_name_classname(factory):
    return get_name(factory, factory.__name__.lower())

def get_provides(factory):
    provides = directive.provides.get(factory)

    if provides is None:
        martian.util.check_implements_one(factory)
        provides = list(interface.implementedBy(factory))[0]
    return provides


class ContextGrokker(martian.GlobalGrokker):

    priority = 1001

    def grok(self, name, module, module_info, config, **kw):
        context = determine_module_component(module_info, directive.context,
                                             [grokcore.component.Context])
        # XXX this depends on the particular implementation of the
        # directive storages :(
        dotted_name = 'grokcore.component.directive.context'
        setattr(module, dotted_name, context)
        return True


class AdapterGrokker(martian.ClassGrokker):
    component_class = grokcore.component.Adapter

    def grok(self, name, factory, module_info, config, **kw):
        adapter_context = get_context(factory, module_info)
        provides = get_provides(factory)
        name = directive.name.get(factory)

        config.action(
            discriminator=('adapter', adapter_context, provides, name),
            callable=component.provideAdapter,
            args=(factory, (adapter_context,), provides, name),
            )
        return True


class MultiAdapterGrokker(martian.ClassGrokker):
    component_class = grokcore.component.MultiAdapter

    def grok(self, name, factory, module_info, config, **kw):
        provides = get_provides(factory)
        name = directive.name.get(factory)

        check_adapts(factory)
        for_ = component.adaptedBy(factory)

        config.action(
            discriminator=('adapter', for_, provides, name),
            callable=component.provideAdapter,
            args=(factory, None, provides, name),
            )
        return True


class GlobalUtilityGrokker(martian.ClassGrokker):
    component_class = grokcore.component.GlobalUtility

    # This needs to happen before the FilesystemPageTemplateGrokker grokker
    # happens, since it relies on the ITemplateFileFactories being grokked.
    priority = 1100

    def grok(self, name, factory, module_info, config, **kw):
        provides = directive.provides.get(factory)
        direct = directive.direct.get(factory)
        name = directive.name.get(factory)

        if direct:
            obj = factory
            if provides is None:
                check_provides_one(factory)
                provides = list(interface.providedBy(factory))[0]
        else:
            obj = factory()
            if provides is None:
                provides = get_provides(factory)

        config.action(
            discriminator=('utility', provides, name),
            callable=component.provideUtility,
            args=(obj, provides, name),
            )
        return True


class AdapterDecoratorGrokker(martian.GlobalGrokker):

    def grok(self, name, module, module_info, config, **kw):
        context = directive.context.get(module)
        implementers = module_info.getAnnotation('implementers', [])
        for function in implementers:
            interfaces = getattr(function, '__component_adapts__', None)
            if interfaces is None:
                # There's no explicit interfaces defined, so we assume the
                # module context to be the thing adapted.
                check_module_component(function, context, 'context',
                                       directive.context)
                interfaces = (context, )

            config.action(
                discriminator=('adapter', interfaces, function.__implemented__),
                callable=component.provideAdapter,
                args=(function, interfaces, function.__implemented__),
                )
        return True


class GlobalUtilityDirectiveGrokker(martian.GlobalGrokker):

    def grok(self, name, module, module_info, config, **kw):
        infos = directive.global_utility.get(module)

        for info in infos:
            provides = info.provides

            if info.direct:
                obj = info.factory
                if provides is None:
                    check_provides_one(obj)
                    provides = list(interface.providedBy(obj))[0]
            else:
                obj = info.factory()
                if provides is None:
                    provides = get_provides(info.factory)

            config.action(
                discriminator=('utility', provides, info.name),
                callable=component.provideUtility,
                args=(obj, provides, info.name),
                )

        return True


class SubscriberGrokker(martian.GlobalGrokker):

    def grok(self, name, module, module_info, config, **kw):
        subscribers = module_info.getAnnotation('grok.subscribers', [])

        for factory, subscribed in subscribers:
            config.action(
                discriminator=None,
                callable=component.provideHandler,
                args=(factory, subscribed),
                )

            for iface in subscribed:
                config.action(
                    discriminator=None,
                    callable=zope.component.interface.provideInterface,
                    args=('', iface)
                    )
        return True
