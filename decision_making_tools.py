from enum import Enum, auto
from copy import deepcopy
from random import random

class Confidence(Enum):
	COMPLETELY = auto()
	MOSTLY     = auto()
	SOMEWHAT   = auto()
	NONE       = auto()

class Comparison(Enum):
	IS_PREFERRED_TO   = auto()
	IS_DISFAVOURED_TO = auto()
	IS_EQUIVALENT_TO  = auto()

# Helper function since I couldn't figure out how to make this work with magic functions (or otherwise)
# TODO should this be a class function of the Comparison enum?
def invert( comparison ):
	if not ( isinstance( comparison, Comparison ) ):
		raise TypeError( 'The value being inverted must be of type DecisionMakingTools.Comparison' )
	if ( comparison == Comparison.IS_PREFERRED_TO ):
		return Comparison.IS_DISFAVOURED_TO
	if ( comparison == Comparison.IS_DISFAVOURED_TO ):
		return Comparison.IS_PREFERRED_TO
	if ( comparison == Comparison.IS_EQUIVALENT_TO ):
		return Comparison.IS_EQUIVALENT_TO
	return comparison	

# Helper class which is essentially a slightly more complex version of a struct / tuple which can carry around 
# metadata associated with a particular value
class DecisionValue:
	
	def __init__( self, value , confidence = Confidence.COMPLETELY, reasoning = 'No reasoning provided' ):
		if not ( isinstance( confidence, Confidence ) ):
			raise TypeError( 'A DecisionValue requires confidence to be of type DecisionMakingTools.Confidence' )
		if not ( isinstance( reasoning, str ) ):
			raise TypeError( 'A DecisionValue requires reasoning to be of type string' )

		self.value = value
		self.confidence = confidence
		self.reasoning = reasoning
		
	# Should probably include __str__() but I don't fully get the rationale for how to choose
	def __repr__( self ):
		return ( 'DecisionValue with value = `{self.value}` confidence = `{self.confidence}` reasoning = `{self.reasoning}`'.format( self=self ) )

def dict_print_rounded( src_dict ):
	print( { k : round(v,2) for k, v in src_dict.items() } )

class PairwiseComparisonMatrix:

	"""
import importlib
importlib.reload( decision_making_tools )
from decision_making_tools import PairwiseComparisonMatrix,Comparison,Confidence,dict_print_rounded
alternatives = ['A1','A2','A3','A4']
pcm = decision_making_tools.PairwiseComparisonMatrix( alternatives )
#print( str( pcm ) )
pcm.is_complete()
pcm.add_comparison('A1', Comparison.IS_DISFAVOURED_TO, 'A2', Confidence.MOSTLY )
pcm.add_comparison('A1', Comparison.IS_PREFERRED_TO,   'A3', Confidence.NONE, 'Because I am very confused' )
pcm.add_comparison('A1', Comparison.IS_PREFERRED_TO,   'A4', Confidence.SOMEWHAT )
pcm.add_comparison('A2', Comparison.IS_PREFERRED_TO,   'A3' )
pcm.add_comparison('A2', Comparison.IS_PREFERRED_TO,   'A4' )
pcm.add_comparison('A3', Comparison.IS_DISFAVOURED_TO, 'A4', Confidence.SOMEWHAT )
print( str( pcm ) )
pcm.is_complete()
pcm.generate_totals()
pcm.generate_weights()
pcm.generate_weights( mutate = True )
dict_print_rounded( pcm.generate_weights( mutate = True, iterations = 10000) )
dict_print_rounded( pcm.generate_weights() )
pcm.simple_display()
	"""

	def __init__( self, alternatives ):
		if not ( isinstance( alternatives, list ) ):
			raise TypeError( 'A pairwise comparison requires a list of alternatives' )
		if not ( len( alternatives ) > 1  ):
			raise ValueError( 'A pairwise comparison requires at least 2 (>= 2) or (>1) alternatives' )

		# This is the only place where aliasing to the "outside" should be a possibility.
		self.alternatives = deepcopy( alternatives )

		self.comparisons_table = dict()

		# I don't really like pre-allocating but it seems like it might be the easiest choice because it makes it clear is something hasn't been completed
		for current_row in self.alternatives:
			self.comparisons_table[ current_row ] = dict()
			for current_column in self.alternatives:
				if ( current_row == current_column ):
					self.comparisons_table[ current_row ][ current_column ] = DecisionValue( Comparison.IS_EQUIVALENT_TO, Confidence.COMPLETELY, 'Logical Consistency' )
				else:
					self.comparisons_table[ current_row ][ current_column ] = None

	def is_complete( self ):
		for current_row in self.alternatives:
			for current_column in self.alternatives:
				if ( self.comparisons_table[current_row][current_column] is None ):
					return False
		return True

	def add_comparison( self, subject, comparison, object, confidence = Confidence.COMPLETELY, reasoning = 'No reasoning provided' ):

		if not ( subject in self.alternatives ):
			raise ValueError( 'The subject alternative `{subject}` must be in the set of alternatives `{self.alternatives}`'.format( subject=subject, self=self ) )
		if not ( isinstance( comparison, Comparison ) ):
			raise TypeError( 'The comparison must be of type DecisionMakingTools.Comparison' )
		if ( comparison == Comparison.IS_EQUIVALENT_TO ):
			raise TypeError( 'In a Pairwise Comparison you are not allowed to declare equivalency' )
		if not ( object in self.alternatives ):
			raise ValueError( 'The object alternative `{object}` must be in the set of alternatives `{self.alternatives}`'.format( object=object, self=self ) )
		if not ( isinstance( confidence, Confidence ) ):
			raise TypeError( 'Confidence must be of type DecisionMakingTools.Confidence' )
		if not ( isinstance( reasoning, str ) ):
			raise TypeError( 'Reasoning must be of type string' )
		
		self.comparisons_table[subject][object] = DecisionValue( comparison, confidence, reasoning )
		self.comparisons_table[object][subject] = DecisionValue( invert( comparison ), confidence, reasoning )

	# Add a little syntactic sugar

	def is_preferred_to( self, subject, object, confidence = Confidence.COMPLETELY, reasoning = 'No reasoning provided' ):
		self.add_comparison( subject, Comparison.IS_PREFERRED_TO, object, confidence, reasoning )

	def is_disfavoured_to( self, subject, object, confidence = Confidence.COMPLETELY, reasoning = 'No reasoning provided' ):
		self.add_comparison( subject, Comparison.IS_DISFAVOURED_TO, object, confidence, reasoning )

	def generate_totals( self, mutate = False ):
		if not ( self.is_complete() ):
			raise ValueError( 'This Pairwise Comparison Matrix must be complete to generate totals' )

		current_comparisons_table = self.comparisons_table

		if ( mutate ):
#			print('PRE MUTATION')
#			self.simple_display( current_comparisons_table )

			# Because we're "mutating" the comparisons we'll make a deep copy
			current_comparisons_table = deepcopy( self.comparisons_table )

			# We need to be careful not to "over mutate" because a PCM is "inverse symmetric" about the diagonal
			# We will leverage that in Python lists are ordered (and let's assume immutable in this case)
		
			for ( current_row_index, current_row_alterntive ) in enumerate( self.alternatives ):
				for current_column_index, current_column_alterntive in enumerate( self.alternatives ):
					if ( current_column_index > current_row_index ):
						# We have the potential for a mutation!

						# Pick a random value for this mutation
						current_probability = random()

						# We will take advantage of aliasing. Which makes reasoning more complicated but simplifies the code ::sigh::
						current_comparison = current_comparisons_table[current_row_alterntive][current_column_alterntive]
						current_mirror_comparison = current_comparisons_table[current_column_alterntive][current_row_alterntive]

						if ( ( current_comparison.confidence == Confidence.MOSTLY ) and (current_probability > 0.85) ):
							current_comparison.value = invert( current_comparison.value )
							current_mirror_comparison.value = invert( current_comparison.value )

						if ( ( current_comparison.confidence == Confidence.SOMEWHAT ) and (current_probability > 0.66) ):
							current_comparison.value = invert( current_comparison.value )
							current_mirror_comparison.value = invert( current_comparison.value )

						if ( ( current_comparison.confidence == Confidence.NONE ) and (current_probability > 0.5) ):
							current_comparison.value = invert( current_comparison.value )
							current_mirror_comparison.value = invert( current_comparison.value )
		
#			print('POST MUTATION')
#			self.simple_display( current_comparisons_table )

		result = dict()

		for current_row in self.alternatives:
			result[current_row] = 0
			for current_column in self.alternatives:
				if ( current_comparisons_table[current_row][current_column].value == Comparison.IS_PREFERRED_TO ):
					result[current_row] += 1
		
		return result

	def generate_weights( self, mutate = False, iterations = 1 ):
		# This is overkill since generate_totals() will also do this but better safe than sorry
		if not ( self.is_complete() ):
			raise ValueError( 'This Pairwise Comparison Matrix must be complete to generate weights' )

		totals = dict()
		for current_iteration in range( iterations ):
			current_totals = self.generate_totals( mutate )
			totals = { key: ( totals.get( key, 0 ) + current_totals.get( key, 0 ) )
			           for key in ( set( totals ) | set( current_totals ) ) }

		grand_total = sum( totals.values() )

		result = dict()

		for current_alternative in self.alternatives:
			result[ current_alternative ] = totals[current_alternative] / grand_total
		
		return result

	def simple_display( self, comparison_table = None ):
		internal_comparison_table = self.comparisons_table
		if ( comparison_table is not None ):
			internal_comparison_table = comparison_table
		result = ''
		# Header row
		result += '\t'
		for current_alternative in self.alternatives:
			result += current_alternative + '\t'
		result += '\n'
		for current_row in self.alternatives:
			result += current_row + '\t'
			for current_column in self.alternatives:
				current_entry = internal_comparison_table[current_row][current_column]
				if ( current_entry is None ):
					result += '?\t'
					continue
				current_comparison = current_entry.value
				if ( current_comparison == Comparison.IS_PREFERRED_TO ):
					result += '1'
				if ( current_comparison == Comparison.IS_DISFAVOURED_TO ):
					result += '0'
				if ( current_comparison == Comparison.IS_EQUIVALENT_TO ):
					result += '-'
				current_confidence = current_entry.confidence
				if ( current_confidence == Confidence.COMPLETELY ):
					result += ' (C)'
				if ( current_confidence == Confidence.MOSTLY ):
					result += ' (M)'
				if ( current_confidence == Confidence.SOMEWHAT ):
					result += ' (S)'
				if ( current_confidence == Confidence.NONE ):
					result += ' (N)'
				result += '\t'
			result += '\n'
		print( result )

	def __str__( self ):
		result = ''
		for current_row in self.alternatives:
			result += 'Row `{current_row}`\n'.format( current_row = current_row )
			for current_column in self.alternatives:
				result += '\tColumn `{current_column}` = `{current_value}`\n'.format( 
					current_column = current_column, current_value = self.comparisons_table[current_row][current_column] 
				)
		return result
