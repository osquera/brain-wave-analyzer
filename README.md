# brain-wave-analyzer
A complete application w. FastAPI frontend and backend that analyzes and visualizes brainwaves.



# Details on implentation
## Loading and filtering

I've never worked with EEG data before but from what I could read on the internet the EEG data needs to be filtered to remove things such as:
- Signal from respiration 
- Signal from muscle artifact 
- Signal from power-line noise 

I mainly used  [this page as my source](https://neuraldatascience.io/7-eeg/erp_filtering.html).

So i guesstimated some ranges for these filters and applied them. 

## Calculating the PSD

Calculating the PSD was pretty straightforward using the mne library. I choose to display the mean of the channels in the PSD plot but I'm unsure if this is 'bad'.

![figures\frequency_band_psd.png](figures\frequency_band_psd.png)

## Comparing the power

Here i calculated the average power in each band:

![figures\avg_power_freq_bands.png](figures\avg_power_freq_bands.png)

And the relative power:

![figures\rel_power_freq_bands.png](figures\rel_power_freq_bands.png)

I found this section of interest in  [the link on 1/f](http://www.scholarpedia.org/article/1/f_noise)

_Linkenkaer-Hansen at el. (2001) showed that both MEG and EEG recordings of spontaneous neural activity in humans displayed 1/f-like power spectra in the α , μ , and β frequency ranges, although the exponents tended to be somewhat less than 1 and differed across the frequency ranges. They suggested that the power-law scaling they observed arose from self-organized criticality occurring within neural networks in the brain. It is possible, however, this inference is not necessarily warranted. One recent study (Bedard et al., 2006) showed that the 1/f scaling of brain local field potentials does not seem to be associated with critical states in the simultaneously-recorded neuronal activities, but rather arises from filtering of the neural signal through the cortical tissue._

We clearly see that the full spectrum has a 1/f trend and if we look at at log plot it becomes clear it follows a power law.

![figures/full_log.png)](figures/full_log.png)