# creation
create and install a local package
https://towardsdatascience.com/building-a-python-package-without-publishing-e2d36c4686cd
create this setup.py file at the top level
install in virtual env with pip install .

# to do
--Time out if no response from comport (MCR not connected to that com port)

# revision history
*update setup.py revision
    v.1.0.5 6/26/2023 added speed variable to focusRel, zoomRel, and irisRel
    v.1.0.4 6/26/2023 changed MCRSendCmd to wait for move to be complete before reading response
                    removed resetting of step position on error, choose expected step position instead
                    added correct for backlash to abs movements
    v.1.0.3 6/23/2023 updated waitTime in MCRMove function to prevent premature timeout
    v.1.0.2 6/22/2023 added timeout function in MCRSendCommand
    v.1.0.1 6/22/2023 added log note to MCRinit
v.1.0.0 6/20/2023 initial versino