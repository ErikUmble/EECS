# code started from template for MIT OCW 6.02, just converted from python 2.7 to 3.8

import numpy, sys, operator
#import PS3_tests

# compute hamming distance of two bit sequences
def hamming(s1, s2):
    return sum(map(operator.xor, s1, s2))


# xor together all the bits in an integer
def xorbits(n):
    result = 0
    while n > 0:
        result ^= (n & 1)
        n >>= 1
    return result


def expected_parity(from_state, to_state, k, glist):
    # x[n] comes from to_state
    # x[n-1] ... x[n-k-1] comes from from_state
    x = ((to_state >> (k - 2)) << (k - 1)) + from_state
    return [xorbits(g & x) for g in glist]


def convolutional_encoder(bits, K, glist):
    result = [0] * (len(bits) * len(glist))
    state = 0
    index = 0
    for b in bits:
        state = (b << (K - 1)) + (state >> 1)
        for g in glist:
            result[index] = xorbits(state & g)
            index += 1
    return numpy.array(result, dtype=numpy.single)


def ber(xmit, received):
    return numpy.sum((xmit != received) * 1) / float(len(xmit))


class ViterbiDecoder:
    # Given the constraint length and a list of parity generator
    # functions, do the initial set up for the decoder.  The
    # following useful instance variables are created:
    #   self.K
    #   self.nstates
    #   self.r
    #   self.predecessor_states
    #   self.expected_parity
    def __init__(self, K, glist):
        self.K = K  # constraint length
        self.nstates = 2 ** (K - 1)  # number of states in state machine

        # number of parity bits transmitted for each message bit
        self.r = len(glist)

        # States are named using (K-1)-bit integers in the range 0 to
        # nstates-1. The bit representation of the integer corresponds
        # to state label in the transition diagram.  So state 10 is
        # named with the integer 2, state 00 is named with the
        # integer 0.

        # for each state s, figure out the two states in the diagram
        # that have transitions ending at state s.  Record these two
        # states as a two-element tuple.
        self.predecessor_states = \
            [((2 * s + 0) % self.nstates, (2 * s + 1) % self.nstates)
             for s in range(self.nstates)]

        # this is a 2D table implemented as a list of lists.
        # self.expected_parity[s1][s2] returns the r-bit sequence
        # of parity bits the encoder transmitted when make the
        # state transition from s1 to s2.
        self.expected_parity = \
            [[expected_parity(s1, s2, K, glist)
              if s1 in self.predecessor_states[s2] else None
              for s2 in range(self.nstates)]
             for s1 in range(self.nstates)]

    # expected is an r-element list of the expected parity bits.
    # received is an r-element list of actual sampled voltages for the
    # incoming parity bits.  This is a hard-decision branch metric,
    # so, as described in lab write up, digitize the received voltages
    # to get bits and then compute the Hamming distance between the
    # expected sequence and the received sequence, return that as the
    # branch metric.  Consider using PS3_tests.hamming(seq1,seq2) which
    # computes the Hamming distance between two binary sequences.
    def branch_metric(self, expected, received):
        # hard decision
        recieved = [1 if v >= 0.5 else 0 for v in received]
        return hamming(expected, recieved)

    # Compute self.PM[...,n] from the batch of r parity bits and the
    # path metrics for self.PM[...,n-1] computed on the previous
    # iteration.  Consult the method described in the lab write up.
    # In addition to making an entry for self.PM[s,n] for each state
    # s, keep track of the most-likely predecessor for each state in
    # the self.Predecessor array (a two-dimensional array indexed by s
    # and n).  You'll probably find the following instance variables
    # and methods useful: self.predecessor_states, self.expected_parity,
    # and self.branch_metric().  To see what these mean, scan through the
    # code above.
    def viterbi_step(self, n, received_voltages):
        for state in range(self.nstates):
            # compute the Path Metric from both incoming branches
            pm0 = self.PM[self.predecessor_states[state][0]][n - 1] + \
                  self.branch_metric(self.expected_parity[self.predecessor_states[state][0]][state], received_voltages)
            pm1 = self.PM[self.predecessor_states[state][1]][n - 1] + \
                  self.branch_metric(self.expected_parity[self.predecessor_states[state][1]][state], received_voltages)

            if pm1 < pm0:
                self.Predecessor[state][n] = self.predecessor_states[state][1]
                self.PM[state][n] = pm1
            else:
                self.Predecessor[state][n] = self.predecessor_states[state][0]
                self.PM[state][n] = pm0

    # Identify the most-likely ending state of the encoder by
    # finding the state s that has the minimum value of PM[s,n]
    # where n points to the last column of the trellis.  If there
    # are several states with the same minimum value, choose one
    # arbitrarily.  Return the state s.
    def most_likely_state(self, n):
        min_state = 0
        for state in range(self.nstates):
            if self.PM[state][n] < self.PM[min_state][n]:
                min_state = state
        return min_state

    # Starting at state s at time n, use the Predecessor
    # array to find all the states on the most-likely
    # path (in reverse order since we're tracing back through
    # the trellis).  Each state contributes a message bit.
    # Return the decoded message as a sequence of 0's and 1's.
    def traceback(self, s, n):
        # start the reverse message with the digits in the last state
        rev_message = []
        # by adding the last state digits in order, then reversing
        for i in range(self.K - 1):
            rev_message.append((s >> i) % 2)
        rev_message.reverse()
        for t in range(n, -1, -1):
            s = self.Predecessor[s][t]
            # add the last digit from the state to the reverse message
            rev_message.append(s % 2)


        rev_message.reverse()
        # remove the initial K - 1 zeros
        for i in range(self.K):
            rev_message.pop(0)
        return rev_message

    # Figure out what the transmitter sent from info in the
    # received voltages.
    def decode(self, received_voltages, debug=False):
        # figure out how many columns are in the trellis
        nreceived = len(received_voltages)
        max_n = int((nreceived / self.r) + 1)

        # this is the path metric trellis itself, organized as a
        # 2D array: rows are the states, columns are the time points.
        # PM[s,n] is the metric for the most-likely path through the
        # trellis arriving at state s at time n.
        self.PM = numpy.zeros((self.nstates, max_n), dtype=numpy.single)

        # at time 0, the starting state is the most likely, the other
        # states are "infinitely" worse.
        self.PM[1:self.nstates, 0] = 1000000

        # a 2D array: rows are the states, columns are the time
        # points, contents indicate the predecessor state for each
        # current state.
        self.Predecessor = numpy.zeros((self.nstates, max_n),
                                       dtype=numpy.intc)

        # use the Viterbi algorithm to compute PM
        # incrementally from the received parity bits.
        n = 0
        for i in range(0, nreceived, self.r):
            n += 1

            # Fill in the next columns of PM, Predecessor based
            # on info in the next r incoming parity bits
            self.viterbi_step(n, received_voltages[i:i + self.r])

            # print out what was just added to the trellis state

        if debug:
            print("Final PM table \n")
            for curState in range(0, self.nstates):
                for time in range(len(self.PM[curState, :])):
                    if (self.PM[curState, time]) >= 1000000:
                        print('inf ')
                    else:
                        print('%3d ' % (self.PM[curState, time]))  # print all times for a given state as one row
                print('\n')
            print("\n Final Predecessor table \n")
            for curState in range(0, self.nstates):
                for time in range(len(self.Predecessor[curState, :])):
                    print('%3d ' % (self.Predecessor[curState, time]))  # print all times for a given state as one row
                print('\n')
            print("\n")

        # find the most-likely ending state from the last row
        # of the trellis
        s = self.most_likely_state(n)

        # reconstruct message by tracing the most likely path
        # back through the matrix using self.Predecessor.
        return self.traceback(s, n)

    # print out final path metrics
    def dump_state(self):
        print(self.PM[:, -1])


class SoftViterbiDecoder(ViterbiDecoder):
    # Override the default branch metric with a soft decision metric:
    # the square of the Euclidian distance between the
    # expected and received voltages.
    def branch_metric(self, expected, received):
        bm = 0
        for i in range(len(expected)):
            bm += (expected[i] - received[i]) ** 2
        return bm


if __name__ == '__main__':
    '''constraint_len = 3; glist = (7,5,3)
    d = ViterbiDecoder(constraint_len, glist)

    # first test case: example from lecture
    message = [1,0,1,0,1,1,0,0]
    received = PS3_tests.convolutional_encoder(message, constraint_len, glist)
    print(f"recieved: {received}")
    i = 0
    print( 'TEST', i)
    decoded = numpy.array(d.decode(received, debug=True))
    print( 'Testing without adding noise...')
    if all(message[i] == decoded[i] for i in range(len(message))):
        print( 'Successfully decoded no-noise Test 0: congratulations!')
        print()
    else:
        print( 'Oops... error in decoding no-noise Test', i)
        print( 'Decoded as ', decoded)
        print( 'Correct is', message)
        sys.exit(1)

    # second batch of test cases: different constraint lengths, generators
    nbits = 29
    message = numpy.random.random_integers(0,1,nbits)
    for (constraint_len, glist) in ((3, (7,5)), (4, (0xD,0xE))):
        i = i + 1
        print( 'TEST', i)
        d = ViterbiDecoder(constraint_len, glist)
        received = PS3_tests.convolutional_encoder(message, constraint_len, glist)
        decoded = numpy.array(d.decode(received, debug=True))
        if (message == decoded).all() == True:
            print( 'Successfully decoded no-noise Test', i, ': congratulations!')
            print()
        else:
            print( 'Oops... error in decoding no-noise Test', i)
            print( 'Decoded as', decoded)
            print( 'Correct is', message)
            sys.exit(1)

    # now try some tests with noise
    PS3_tests.test_hard_metrics(ViterbiDecoder)'''

    # Test whether branch metrics are as expected
    '''PS3_tests.test_soft_metrics(SoftViterbiDecoder)

    # This test for soft decoding produces a random message of
    # nbits=1000 in length, from a fixed random seed (so each time the
    # program is run, the same behavior will occur. We encode the
    # message and then use your soft decoder (code above) to test it.
    # If the decoded stream is the same as what we expect from our
    # encoder, we consider the test case to have passed.  Note, it is
    # possible (though not likely) that your soft decoder may not pass
    # this test case, but is in fact correct.  That's why we have not
    # made the test case part of the verification before checkoff.
    K, glist = 3, (7, 5)
    soft = SoftViterbiDecoder(K, glist)
    nbits = 1000
    sigma = 0.5  # noise defined as 2*sigma^2 = 1/8
    numpy.random.seed(617617617)
    message = numpy.random.random_integers(0, 1, nbits)
    expected = numpy.array(
        [1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1,
         1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 0, 0,
         0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1,
         0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1,
         1, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 1,
         1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0,
         1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1,
         1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1,
         0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1,
         1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
         1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1,
         0, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1,
         0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0,
         0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1,
         1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1,
         0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0,
         0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0,
         0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1,
         0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1,
         0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0,
         0, 1, 1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0,
         1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0,
         1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0,
         0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1,
         0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1,
         1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1,
         1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1,
         1])

    encoded = PS3_tests.convolutional_encoder(message, K, glist)

    noisy = numpy.random.normal(0, sigma, len(encoded))
    received = encoded + noisy
    print(received)
    decoded = numpy.array(soft.decode(received))
    if all(decoded[i] == expected[i] for i in range(len(expected))):
        print('Soft decoding succeeded on test case: congratulations!')
    else:
        print('Oops... error in soft decoding')
        print('Decoded as', decoded)
        print('Expected  ', expected)
        print(f"difference: {decoded - expected}")
        sys.exit(1)'''

