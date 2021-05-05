'''Module to import Nipype Pipeline engine and override some Classes.
See https://fcp-indi.github.com/docs/developer/nodes
for C-PAC-specific documentation.
See https://nipype.readthedocs.io/en/latest/api/generated/nipype.pipeline.engine.html
for Nipype's documentation.'''  # noqa E501
import os
from copy import deepcopy
from functools import partialmethod
from nipype import logging
from nipype.pipeline import engine as pe
from nipype.pipeline.engine.utils import (
    _create_dot_graph,
    format_dot,
    generate_expanded_graph,
    get_print_name,
    _replacefunk,
    _run_dot
)
from nipype.utils.filemanip import fname_presuffix

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

        dotlist = ['%slabel="%s";' % (
            f'"{prefix}"' if len(prefix.strip()) else prefix, self.name)]
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
                            '"%s"[label="%s", shape=box3d,'
                            "style=filled, color=black, colorscheme"
                            "=greys7 fillcolor=2];"
                        )
                        % (nodename, node_class_name)
                    )
                else:
                    if colored:
                        dotlist.append(
                            ('"%s"[label="%s", style=filled,'
                             ' fillcolor="%s"];')
                            % (nodename, node_class_name, colorset[level])
                        )
                    else:
                        dotlist.append(
                            ('"%s"[label="%s"];') % (nodename, node_class_name)
                        )

        for node in nx.topological_sort(self._graph):
            if isinstance(node, Workflow):
                fullname = ".".join(hierarchy + [node.fullname])
                nodename = fullname.replace(".", "_")
                dotlist.append("subgraph \"cluster_%s\" {" % nodename)
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
                            dotlist.append('"%s" -> "%s";' % (
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
                        '"%s" -> "%s";'
                        % (uname1.replace(".", "_"), vname1.replace(".", "_"))
                    )
                    logger.debug("cross connection: %s", dotlist[-1])
        return ("\n" + prefix).join(dotlist)

    def write_graph(
        self,
        dotfilename="graph.dot",
        graph2use="hierarchical",
        format="png",
        simple_form=True,
    ):
        graphtypes = ["orig", "flat", "hierarchical", "exec", "colored"]
        if graph2use not in graphtypes:
            raise ValueError(
                "Unknown graph2use keyword. Must be one of: " + str(graphtypes)
            )
        base_dir, dotfilename = os.path.split(dotfilename)
        if base_dir == "":
            if self.base_dir:
                base_dir = self.base_dir
                if self.name:
                    base_dir = os.path.join(base_dir, self.name)
            else:
                base_dir = os.getcwd()
        os.makedirs(base_dir, exist_ok=True)
        if graph2use in ["hierarchical", "colored"]:
            if self.name[:1].isdigit():  # these graphs break if int
                raise ValueError(
                    "{} graph failed, workflow name cannot begin "
                    "with a number".format(graph2use)
                )
            dotfilename = os.path.join(base_dir, dotfilename)
            self.write_hierarchical_dotfile(
                dotfilename=dotfilename,
                colored=graph2use == "colored",
                simple_form=simple_form,
            )
            outfname = format_dot(dotfilename, format=format)
        else:
            graph = self._graph
            if graph2use in ["flat", "exec"]:
                graph = self._create_flat_graph()
            if graph2use == "exec":
                graph = generate_expanded_graph(deepcopy(graph))
            outfname = export_graph(
                graph,
                base_dir,
                dotfilename=dotfilename,
                format=format,
                simple_form=simple_form,
            )

        logger.info(
            "Generated workflow graph: %s (graph2use=%s, simple_form=%s)."
            % (outfname, graph2use, simple_form)
        )
        return outfname

    write_graph.__doc__ = pe.Workflow.write_graph.__doc__

    def write_hierarchical_dotfile(
        self, dotfilename=None, colored=False, simple_form=True
    ):
        dotlist = ["digraph \"%s\"{" % self.name]
        dotlist.append(
            self._get_dot(prefix="  ", colored=colored,
                          simple_form=simple_form)
        )
        dotlist.append("}")
        dotstr = "\n".join(dotlist)
        if dotfilename:
            fp = open(dotfilename, "wt")
            fp.writelines(dotstr)
            fp.close()
        else:
            logger.info(dotstr)


def export_graph(
    graph_in,
    base_dir=None,
    show=False,
    use_execgraph=False,
    show_connectinfo=False,
    dotfilename="graph.dot",
    format="png",
    simple_form=True,
):
    """Displays the graph layout of the pipeline
    This function requires that pygraphviz and matplotlib are available on
    the system.
    Parameters
    ----------
    show : boolean
    Indicate whether to generate pygraphviz output fromn
    networkx. default [False]
    use_execgraph : boolean
    Indicates whether to use the specification graph or the
    execution graph. default [False]
    show_connectioninfo : boolean
    Indicates whether to show the edge data on the graph. This
    makes the graph rather cluttered. default [False]
    """
    import networkx as nx

    graph = deepcopy(graph_in)
    if use_execgraph:
        graph = generate_expanded_graph(graph)
        logger.debug("using execgraph")
    else:
        logger.debug("using input graph")
    if base_dir is None:
        base_dir = os.getcwd()

    os.makedirs(base_dir, exist_ok=True)
    out_dot = fname_presuffix(
        dotfilename, suffix="_detailed.dot", use_ext=False, newpath=base_dir
    )
    _write_detailed_dot(graph, out_dot)

    # Convert .dot if format != 'dot'
    outfname, res = _run_dot(out_dot, format_ext=format)
    if res is not None and res.runtime.returncode:
        logger.warning("dot2png: %s", res.runtime.stderr)

    pklgraph = _create_dot_graph(graph, show_connectinfo, simple_form)
    simple_dot = fname_presuffix(
        dotfilename, suffix=".dot", use_ext=False, newpath=base_dir
    )
    nx.drawing.nx_pydot.write_dot(pklgraph, simple_dot)

    # Convert .dot if format != 'dot'
    simplefname, res = _run_dot(simple_dot, format_ext=format)
    if res is not None and res.runtime.returncode:
        logger.warning("dot2png: %s", res.runtime.stderr)

    if show:
        pos = nx.graphviz_layout(pklgraph, prog="dot")
        nx.draw(pklgraph, pos)
        if show_connectinfo:
            nx.draw_networkx_edge_labels(pklgraph, pos)

    return simplefname if simple_form else outfname


def _write_detailed_dot(graph, dotfilename):
    r"""
    Create a dot file with connection info ::
        digraph structs {
        node [shape=record];
        struct1 [label="<f0> left|<f1> middle|<f2> right"];
        struct2 [label="<f0> one|<f1> two"];
        struct3 [label="hello\nworld |{ b |{c|<here> d|e}| f}| g | h"];
        struct1:f1 -> struct2:f0;
        struct1:f0 -> struct2:f1;
        struct1:f2 -> struct3:here;
        }
    """
    import networkx as nx

    text = ["digraph structs {", "node [shape=record];"]
    # write nodes
    edges = []
    for n in nx.topological_sort(graph):
        nodename = n.itername
        inports = []
        for u, v, d in graph.in_edges(nbunch=n, data=True):
            for cd in d["connect"]:
                if isinstance(cd[0], (str, bytes)):
                    outport = cd[0]
                else:
                    outport = cd[0][0]
                inport = cd[1]
                ipstrip = "in%s" % _replacefunk(inport)
                opstrip = "out%s" % _replacefunk(outport)
                edges.append(
                    '"%s":"%s":e -> "%s":"%s":w;'
                    % (
                        u.itername.replace(".", ""),
                        opstrip,
                        v.itername.replace(".", ""),
                        ipstrip,
                    )
                )
                if inport not in inports:
                    inports.append(inport)
        inputstr = (
            ["{IN"]
            + ["|<in%s> %s" % (_replacefunk(ip), ip) for ip in sorted(inports)]
            + ["}"]
        )
        outports = []
        for u, v, d in graph.out_edges(nbunch=n, data=True):
            for cd in d["connect"]:
                if isinstance(cd[0], (str, bytes)):
                    outport = cd[0]
                else:
                    outport = cd[0][0]
                if outport not in outports:
                    outports.append(outport)
        outputstr = (
            ["{OUT"]
            + [
                "|<out%s> %s" % (_replacefunk(oport), oport)
                for oport in sorted(outports)
            ]
            + ["}"]
        )
        srcpackage = ""
        if hasattr(n, "_interface"):
            pkglist = n.interface.__class__.__module__.split(".")
            if len(pkglist) > 2:
                srcpackage = pkglist[2]
        srchierarchy = ".".join(nodename.split(".")[1:-1])
        nodenamestr = "{ %s | %s | %s }" % (
            nodename.split(".")[-1],
            srcpackage,
            srchierarchy,
        )
        text += [
            '"%s" [label="%s|%s|%s"];'
            % (
                nodename.replace(".", ""),
                "".join(inputstr),
                nodenamestr,
                "".join(outputstr),
            )
        ]
    # write edges
    for edge in sorted(edges):
        text.append(edge)
    text.append("}")
    with open(dotfilename, "wt") as filep:
        filep.write("\n".join(text))
    return text
