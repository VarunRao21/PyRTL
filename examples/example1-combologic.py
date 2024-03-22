""" Example 1:  A simple combination logic block example.

    This example declares a block of hardware with three one-bit inputs,
    (a,b,c) and two one-bit outputs (sum, cout).  The logic declared is a
    simple one-bit adder and the definition uses some of the most common
    parts of PyRTL. The adder is then simulated on random data, the
    wave form is printed to the screen, and the resulting trace is
    compared to a "correct" addition.  If the result is correct then a 0
    is returned, else 1.
"""

import random
import pyrtl

# The basic idea of PyRTL is to specify the component of a some hardware block
# through the declaration of wires and operations on those wires.  The current
# working block, an instance of a class devilishly named "Block", is implicit
# in all of the below code -- it is easiest to start with the way wires work.

# --- Step 1: Define Logic -------------------------------------------------

# One of the most fundamental types in PyRTL is the "WireVector" which acts
# very much like a Python list of 1-bit wires.  Unlike a normal list, though, the
# number of bits is explicitly declared.
temp1 = pyrtl.WireVector(bitwidth=1, name='temp1')

# Both arguments are in fact optional and default to a bitwidth of 1 and a unique
# name generated by PyRTL starting with 'tmp'
temp2 = pyrtl.WireVector()

# Two special types of WireVectors are Input and Output, which are used to specify
# an interface to the hardware block.
a, b, c = pyrtl.Input(1, 'a'), pyrtl.Input(1, 'b'), pyrtl.Input(1, 'c')
sum, carry_out = pyrtl.Output(1, 'sum'), pyrtl.Output(1, 'carry_out')

# Okay, let's build a one-bit adder.  To do this we need to use the assignment
# operator, which is '<<='.  This takes an already declared wire and "connects"
# it to some other already declared wire.  Let's start with the sum bit, which is
# of course just the xor of the three inputs
sum <<= a ^ b ^ c

# The carry_out bit would just be "carry_out <<= a & b | a & c | b & c" but let's break
# than down a bit to see what is really happening.  What if we want to give names
# to the partial signals in the middle of that computation?  When you take
# "a & b" in PyRTL, what that really means is "make an AND gate, connect one input
# to 'a' and the other to 'b' and return the result of the gate".  The result of
# that AND gate can then be assigned to temp1 or it can be used like any other
# Python variable.

temp1 <<= a & b  # connect the result of a & b to the pre-allocated wirevector
temp2 <<= a & c
temp3 = b & c  # temp3 IS the result of b & c (this is the first mention of temp3)
carry_out <<= temp1 | temp2 | temp3

# You can access the working block through pyrtl.working_block(), and for most
# things one block is all you will need.  Example 2 discusses this in more detail,
# but for now we can just print the block to see that in fact it looks like the
# hardware we described.  The format is a bit weird, but roughly translates to
# a list of gates (the 'w' gates are just wires).  The ins and outs of the gates
# are printed 'name'/'bitwidth''WireVectorType'

print('--- One Bit Adder Implementation ---')
print(pyrtl.working_block())
print()

# --- Step 2: Simulate Design  -----------------------------------------------

# Okay, let's simulate our one-bit adder.  To keep track of the output of
# the simulation we need to make a new "SimulationTrace" and a "Simulation"
# that then uses that trace.

sim_trace = pyrtl.SimulationTrace()
sim = pyrtl.Simulation(tracer=sim_trace)

# Now all we need to do is call "sim.step" to simulate each clock cycle of our
# design.  We just need to pass in some input each cycle, which is a dictionary
# mapping inputs (the *names* of the inputs, not the actual Input instances)
# to their value for that signal each cycle.  In this simple example, we
# can just specify a random value of 0 or 1 with Python's random module.  We
# call step 15 times to simulate 15 cycles.

for cycle in range(15):
    sim.step({
        'a': random.choice([0, 1]),
        'b': random.choice([0, 1]),
        'c': random.choice([0, 1])
    })

# Now all we need to do is print the trace results to the screen. Here we use
# "render_trace" with some size information.
print('--- One Bit Adder Simulation ---')
sim_trace.render_trace(symbol_len=2)

a_value = sim.inspect(a)
print("The latest value of 'a' was: " + str(a_value))

# --- Step 3: Verification of Simulated Design ---------------------------------------

# Now finally, let's check the trace to make sure that sum and carry_out are actually
# the right values when compared to Python's addition operation.  Note that
# all the simulation is done at this point and we are just checking the waveform,
# but there is no reason you could not do this at simulation time if you had a
# really long-running design.

for cycle in range(15):
    # Note that we are doing all arithmetic on values, NOT wirevectors, here.
    # We can add the inputs together to get a value for the result
    add_result = (sim_trace.trace['a'][cycle]
                  + sim_trace.trace['b'][cycle]
                  + sim_trace.trace['c'][cycle])
    # We can select off the bits and compare
    python_sum = add_result & 0x1
    python_cout = (add_result >> 1) & 0x1
    if (python_sum != sim_trace.trace['sum'][cycle]
            or python_cout != sim_trace.trace['carry_out'][cycle]):
        print('This Example is Broken!!!')
        exit(1)

# You made it to the end!
exit(0)
