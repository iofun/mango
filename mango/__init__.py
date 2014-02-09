# -*- coding: utf-8 -*-
'''
    Mango system primitives.
'''

# This file is part of mango.

# Distributed under the terms of the last AGPL License. 
# The full license is in the file LICENCE, distributed as part of this software.

'''
    The Actor model
    ---------------
    A mathematical theory that treats "Actors" as the universal primitives of
    concurrent digital computation.

    The model has been used both as a framework for a theoretical understanding
    of concurrency, and as the theoretical basis for several practical 
    implementations of concurrent systems.

    Unlike previous models of computation, the Actor model was inspired by physical laws.

    It was also influenced by the programming languages Lisp, Simula 67 and Smalltalk-72,
    as well as ideas for Petri Nets, capability-based systems and packet switching.

    Actor technology will see significant application for integrating all kinds
    of digital information for individuals, groups, and organizations so their
    information usefully links together.


    Information integration is all about to make use of the following system principles:

    Persistence.
        Information is collected and indexed.

    Concurrency:
        Work proceeds interactively and concurrently, overlapping in time.

    Quasi-commutativity:
       Information can be used regardless of whether it initiates new work
       or become relevant to ongoing work.

    Sponsorship:
       Sponsors provide resources for computation, i.e., processing, storage, and communications.

    Pluralism:
       Information is heterogeneous, overlapping and often inconsistent.

    Provenance:
       The provenance of information is carefully tracked and recorded.


    The Actor Model is intended to provide a foundation for inconsistency robust information integration.
    http://arxiv.org/abs/1008.1459
'''

__author__ = 'Jean Chassoul'
