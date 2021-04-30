'''Module to import Nipype Pipeline engine and override some Classes.
See https://fcp-indi.github.com/docs/developer/nodes
for C-PAC-specific documentation.
See https://nipype.readthedocs.io/en/latest/api/generated/nipype.pipeline.engine.html
for Nipype's documentation.'''  # noqa E501
from nipype import logging
from nipype.pipeline import engine as pe
from nipype.pipeline.engine.utils import get_print_name
from functools import partialmethod

logger = logging.getLogger("nipype.workflow")

# set global default mem_gb
DEFAULT_MEM_GB = 2.0


def _doctest_skiplines(docstring, lines_to_skip):
    '''
    Function to add '  # doctest: +SKIP' to the end of docstring lines
    to skip in imported docstrings.

    Parameters
    ----------
    docstring: str

    lines_to_skip: set or list

    Returns
    -------
    docstring: str

    Examples
    --------
    >>> _doctest_skiplines('skip this line', {'skip this line'})
    'skip this line  # doctest: +SKIP'
    '''
    if (
        not isinstance(lines_to_skip, set) and
        not isinstance(lines_to_skip, list)
    ):
        raise TypeError(
            '_doctest_skiplines: `lines_to_skip` must be a set or list.')

    return '\n'.join([
        f'{line}  # doctest: +SKIP' if line in lines_to_skip else line
        for line in docstring.split('\n')
    ])


class Node(pe.Node):
    __doc__ = _doctest_skiplines(
        pe.Node.__doc__,
        {"    >>> realign.inputs.in_files = 'functional.nii'"}
    )

    __init__ = partialmethod(pe.Node.__init__, mem_gb=DEFAULT_MEM_GB)


class MapNode(pe.MapNode):
    __doc__ = _doctest_skiplines(
        f'mem_gb={DEFAULT_MEM_GB}\n\nn_procs=1\n\n{pe.MapNode.__doc__}',
        {"    ...                           'functional3.nii']"}
    )

    __init__ = partialmethod(pe.MapNode.__init__, mem_gb=DEFAULT_MEM_GB,
                             n_procs=1)


class Workflow(pe.Workflow):
    def _get_dot(
        self, prefix=None, hierarchy=None, colored=False, simple_form=True,
        level=0
    ):
        """Create a dot file with connection info"""
        import networkx as nx

        if prefix is None:
            prefix = "  "
        if hierarchy is None:
            hierarchy = []
        colorset = [
            "#FFFFC8",  # Y
            "#0000FF",
            "#B4B4FF",
            "#E6E6FF",  # B
            "#FF0000",
            "#FFB4B4",
            "#FFE6E6",  # R
            "#00A300",
            "#B4FFB4",
            "#E6FFE6",  # G
            "#0000FF",
            "#B4B4FF",
        ]  # loop B
        if level > len(colorset) - 2:
            level = 3  # Loop back to blue

        dotlist = ['%slabel="%s";' % (prefix, self.name)]
        for node in nx.topological_sort(self._graph):
            fullname = ".".join(hierarchy + [node.fullname])
            nodename = fullname.replace(".", "_")
            if not isinstance(node, Workflow):
                node_class_name = get_print_name(node, simple_form=simple_form)
                if not simple_form:
                    node_class_name = ".".join(node_class_name.split(".")[1:])
                if hasattr(node, "iterables") and node.iterables:
                    dotlist.append(
                        (
                            '%s[label="%s", shape=box3d,'
                            "style=filled, color=black, colorscheme"
                            "=greys7 fillcolor=2];"
                        )
                        % (nodename, node_class_name)
                    )
                else:
                    if colored:
                        dotlist.append(
                            ('%s[label="%s", style=filled,'
                             ' fillcolor="%s"];')
                            % (nodename, node_class_name, colorset[level])
                        )
                    else:
                        dotlist.append(
                            ('%s[label="%s"];') % (nodename, node_class_name)
                        )

        for node in nx.topological_sort(self._graph):
            if isinstance(node, Workflow):
                fullname = ".".join(hierarchy + [node.fullname])
                nodename = fullname.replace(".", "_")
                dotlist.append("subgraph cluster_%s {" % nodename)
                if colored:
                    dotlist.append(
                        prefix + prefix + 'edge [color="%s"];' % (
                            colorset[level + 1])
                    )
                    dotlist.append(prefix + prefix + "style=filled;")
                    dotlist.append(
                        prefix + prefix + 'fillcolor="%s";' % (
                            colorset[level + 2])
                    )
                dotlist.append(
                    node._get_dot(
                        prefix=prefix + prefix,
                        hierarchy=hierarchy + [self.name],
                        colored=colored,
                        simple_form=simple_form,
                        level=level + 3,
                    )
                )
                dotlist.append("}")
            else:
                for subnode in self._graph.successors(node):
                    if node._hierarchy != subnode._hierarchy:
                        continue
                    if not isinstance(subnode, Workflow):
                        nodefullname = ".".join(hierarchy + [node.fullname])
                        subnodefullname = ".".join(
                            hierarchy + [subnode.fullname])
                        nodename = nodefullname.replace(".", "_")
                        subnodename = subnodefullname.replace(".", "_")
                        for _ in self._graph.get_edge_data(
                            node, subnode
                        )["connect"]:
                            dotlist.append("%s -> %s;" % (
                                nodename, subnodename))
                        logger.debug("connection: %s", dotlist[-1])
        # add between workflow connections
        for u, v, d in self._graph.edges(data=True):
            uname = ".".join(hierarchy + [u.fullname])
            vname = ".".join(hierarchy + [v.fullname])
            for src, dest in d["connect"]:
                uname1 = uname
                vname1 = vname
                if isinstance(src, tuple):
                    srcname = src[0]
                else:
                    srcname = src
                if "." in srcname:
                    uname1 += "." + ".".join(srcname.split(".")[:-1])
                if "." in dest and "@" not in dest:
                    if not isinstance(v, Workflow):
                        if "datasink" not in str(
                            v._interface.__class__
                        ).lower():
                            vname1 += "." + ".".join(dest.split(".")[:-1])
                    else:
                        vname1 += "." + ".".join(dest.split(".")[:-1])
                if uname1.split(".")[:-1] != vname1.split(".")[:-1]:
                    dotlist.append(
                        "%s -> %s;"
                        % (uname1.replace(".", "_"), vname1.replace(".", "_"))
                    )
                    logger.debug("cross connection: %s", dotlist[-1])
        return ("\n" + prefix).join(dotlist)
