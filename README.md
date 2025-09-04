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

