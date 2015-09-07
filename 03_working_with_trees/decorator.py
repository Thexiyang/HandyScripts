#!/usr/bin/env python

__author__ = "Joel Boyd"
__copyright__ = "Copyright 2015"
__credits__ = ["Joel Boyd"]
__license__ = "GPL3"
__maintainer__ = "Joel Boyd"
__email__ = "joel.boyd near uq.net.au"
__status__ = "Development"
__version__ = "0.0.1"

################################################################################
################################# - Imports - ##################################

# System imports
from skbio import TreeNode
import argparse
import logging
import os
import sys

################################################################################
################################# - Setup - ####################################

debug={1:logging.CRITICAL,
       2:logging.ERROR,
       3:logging.WARNING,
       4:logging.INFO,
       5:logging.DEBUG}

################################################################################
################################## - Code - ####################################

class TreeDecorator:
    '''Yet another class that decorates trees, only the way I want it.'''
    def __init__(self, 
                 tree_path,
                 taxonomy):
        '''
        Set up empty lists and open and import tree object, and load the
        taxonomy into a hash
        '''
        
        self.gg_prefixes = ["k__", 'p__', 'c__', 'o__', 'f__', 'g__', 's__']
        
        # Set empty list to record nodes that have already been assigned
        # taxonomy.
        self.encountered_nodes = {}
        self.encountered_taxonomies = set()
        
        # Read in tree
        logging.info("Importing tree from file: %s" % (tree_path))
        self.tree = TreeNode.read(
                        open(tree_path, "r")
                                )  
        
        # Read in taxonomy
        logging.info("Importing taxonomy from file: %s" % (taxonomy))
        self.taxonomy = {}
        for entry in open(taxonomy, "r"):
            entry = entry.strip().split('\t')
            self.taxonomy[entry[0]] = (entry[1].split('; ') if '; ' in entry[1]\
                                       else entry[1].split(';'))
        
    def _nodes(self):
        '''
        Iterate through nodes in tree, returning those that are not tips (i.e.
        returning only nodes)
        
        Inputs:
            None
        Yields:
            Node object, if it is not a tip
        '''
        logging.debug("Iterating through nodes")
        for node in self.tree.preorder():
            if node.is_root():
                logging.debug("%i reads in tree from root" % (len(list(node.tips()))))
            elif node.is_tip():
                logging.debug("Tip %s reached" % (node.name))
            else:
                if node not in self.encountered_nodes: # If node hath not been decorated.
                    if node.name:
                        logging.debug("Node %s reached" % (node.name))
                    else:
                        logging.debug("Unnamed node reached")
                    yield node
    
    def _transpose_taxonomy(self, taxonomy_list):
        '''
        Transpose the taxonomy grid to contain lists of each taxonomic
        rank
        
        Inputs: 
            taxonomy_list: array
                - List of split taxonomy strings to be tansposed
        Outputs: 
            transposed_taxonomy: array
                - As per above description
        '''
        transposed_taxonomy = []
        for index in range(0, 7):
            rank_taxonomy_list = [taxonomy_entry[index] 
                                    for taxonomy_entry in taxonomy_list]
            transposed_taxonomy.append(set(rank_taxonomy_list))
        return transposed_taxonomy
    
    def _write_tree(self, output):
        '''Just Writes tree to file uisng scikit-bio'''
        logging.info("Writing decorated tree to file: %s" % (output))
        self.tree.write(
                    output,
                    format = "newick"
                        )
        
    def _write_consensus_strings(self, output):
        '''Writes the taxonomy of each leaf to a file'''
        logging.info("Writing decorated taxonomy to file: %s" % (output))
        with open(output, 'w') as out:
            for tip in self.tree.tips():
                ancestors = tip.ancestors()
                tax_list = list(reversed([x.name for x in ancestors if x.name]))
                tax_name = tip.name.replace(" ", "_")
                if len(tax_list) < 1:
                    logging.debug("Species %s not decorated within the tree, using provided tax string as substitute" % (tax_name))
                    if tax_name in self.taxonomy:
                        tax_string = '; '.join(self.taxonomy[tax_name])
                    else:
                        logging.warning("No taxonomy found for species %s!" % (tax_name))
                        tax_string = "Unknown"
                else:
                    tax_string = '; '.join(tax_list)
                output_line = "%s\t%s\n" % (tax_name, tax_string)
                out.write(output_line)
    
    def _get_tax_index(self, ancestry):
        '''
        Iterate through ancestor nodes to find the current taxonomy index (i.e.
        the rank that should be assigned to the current node.
        
        Inputs:
            ancestry: list
                TreeNode.ancestory list that contains all nodes above the 
                current.
        Outputs:
            Current index of taxonomy. Returns None if node has no ancestors 
            (i.e. is root)
                
        '''
        current_index = 0
        ancestry = [x for x in ancestry if not x.is_root()]
        if any(ancestry):
            ancestor_tax_list = []
            for ancestor in ancestry:
                ai = self.encountered_nodes[ancestor]
                if ancestor.name:
                    ancestor_tax_list.append(ancestor.name)
                if ai > current_index:
                    current_index = ai
            ancestor_tax = '; '.join(reversed(ancestor_tax_list))
            logging.debug("Ancestors at %i nodes: %s" % (len(ancestor_tax_list), ancestor_tax))
            ancetor_rank_number = len(ancestor_tax.split('; ')) #
            return current_index, ancetor_rank_number
        else:       
            raise Exception("Programming error in _get_tax_index. Failed to find ancestors for current node.")
    
    def extract(self, output_tax):
        self._write_consensus_strings(output_tax)
    
    def decorate(self, output_tree, output_tax):
        '''
        Main function for TreeDecorator class. Accepts the output directory, 
        iterates through nodes, classifying them according to provided taxonomy. 
        '''
        # Define list of prefixes
        
        
        logging.info("Decorating tree")
        for node in self._nodes():
            placement_depth = 0 
            current_index = 0
            parent = node.parent
            children = list(node.tips())
            logging.debug("Current node has %i children" % (len(children)))
            
            # Gather the children (creepy voice)
            children_taxonomy = []
            for t in children:
                tip_name = t.name.replace(' ', '_')
                if tip_name in self.taxonomy:
                    children_taxonomy.append(self.taxonomy[tip_name])
            node_tax = self._transpose_taxonomy(children_taxonomy)
            tax_list = []
            for index, rank in enumerate(node_tax):
                if len(rank) == 1:
                    tax=list(rank)[0]
                    if tax not in self.gg_prefixes:
                        tax_list.append(list(rank)[0])
                    placement_depth += 1
                else:
                    break
                
            if len(tax_list) >= 1:
                logging.debug("Node has consistent taxonomy: %s" % '; '.join(tax_list))
                if parent.is_root():
                    current_index = len(tax_list)
                else:
                    current_index, resolution = self._get_tax_index(node.ancestors())
                    if len(tax_list) <= current_index:
                        logging.debug("No consistent taxonomy found for node! Moving to next node.")
                        self.encountered_nodes[node]=current_index
                        continue
                    else:
                        if len(tax_list) == placement_depth:
                            tax_list = tax_list[current_index:]
                            for child in children:
                                self.encountered_nodes[child] = current_index
                        elif len(node.children) == len(list(node.tips())):
                            tax_list = tax_list[current_index:]
                            for child in children:
                                self.encountered_nodes[child] = current_index
                        else:
                            current_index = len(tax_list)
                
                if resolution < 7:
                    new_tax_list = [] 
                    for tax in tax_list:
                        if tax in self.encountered_taxonomies:
                            idx=1
                            while tax in self.encountered_taxonomies:
                                if idx > 1: 
                                    tax = '%s_%i' % ('_'.join(tax.split('_')[:-1]), idx)
                                else:
                                    tax = tax + '_%i' % idx
                                idx += 1

                        new_tax_list.append(tax)
                        self.encountered_taxonomies.add(tax)
                    tax_string = '; '.join(new_tax_list)
                    
                    node.name = tax_string
                    logging.debug("Renamed node %s" % tax_string)
                    self.encountered_nodes[node]=index
                    
                else:
                    self.encountered_nodes[node]=current_index
            else:
                logging.debug("Cannot resolve node, no consistent taxonomy beyond that which has been described.")
                self.encountered_nodes[node]=current_index
            
        self._write_tree(output_tree)
        self._write_consensus_strings(output_tax)
        
################################################################################
################################ - argparser - #################################
          
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--version', action='version', version='decorateM v%s' % __version__)
    subparsers = parser.add_subparsers(help="--", dest='subparser_name')
    
    decoratem_parser = subparsers.add_parser('decorate',
                                             description='Decorate a tree the way you want to',
                                             epilog=__author__)
    ### - Inputs options - ###
    input_options = decoratem_parser.add_argument_group('input options')
    input_options.add_argument('--tree', help='Input tree, in newick format only, please.', required=True)
    input_options.add_argument('--taxonomy', help = 'Taxonomy corresponding to all or some of the nodes in the tree.', required=True)
    
    ### - Output options - ###
    output_options = decoratem_parser.add_argument_group('output options')
    output_options.add_argument('--output_tree', help='Output tree file', type=str, required=True)
    output_options.add_argument('--output_tax', help='Decorated taxonomy file', type=str, required=True)
    
    output_options.add_argument('--log', help='Output logging information to file', type=str, default=False)
    output_options.add_argument('--verbosity', help='1 - 5, 1 being silent, 5 being noisy indeed. Default = 4', type=int, default=4)
    
    
    decoratem_parser = subparsers.add_parser('extract',
                                         description='Extract the taxonomy from an already decorated tree',
                                         epilog=__author__)
    input_extract_options = decoratem_parser.add_argument_group('input options')
    input_extract_options.add_argument('--tree', help='Input tree, in newick format only, please.', required=True)
    input_extract_options.add_argument('--taxonomy', help = 'Taxonomy corresponding to all or some of the nodes in the tree.', required=True)
    input_extract_options.add_argument('--output_tax', help='Decorated taxonomy file', type=str, required=True)
    input_extract_options.add_argument('--log', help='Output logging information to file', type=str, default=False)
    input_extract_options.add_argument('--verbosity', help='1 - 5, 1 being silent, 5 being noisy indeed. Default = 4', type=int, default=4)

    args = parser.parse_args()
    
    
        
    if args.log:
        if os.path.isfile(args.log): raise Exception("File %s exists" % args.log)
        logging.basicConfig(filename=args.log, level=debug[args.verbosity], format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    else:
        logging.basicConfig(level=debug[args.verbosity], format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    
    logging.info("Command ran: %s" % ' '.join(sys.argv))
    
    if args.subparser_name == "decorate":
        TreeDecorator(
                args.tree,
                args.taxonomy
                      ).decorate(args.output_tree,
                                 args.output_tax)
    elif args.subparser_name == "extract":
        TreeDecorator(
                args.tree,
                args.taxonomy
                      ).extract(args.output_tax)
################################################################################
################################################################################
        
        