#!/usr/bin/env bash

folder='/sst1m/analyzed/calib/'
ghv_on_folder=$folder'ghv_on/'
ghv_off_folder=$folder'ghv_off/'
dark_folder=$folder'dark/'
timing_folder=$folder'timing/'
fmpe_folder=$folder'fmpe/'
mpe_folder=$folder'mpe/'
baseline_shift_folder=$folder'baseline_shift/'
figure_folder_name='figures/'

raw_histo_name='raw_histo.pk'
max_histo_name='max_histo.pk'
charge_histo_name='charge_histo.pk'
amplitude_histo_name='amplitude_histo.pk'
results_name='results.npz'
timing_histo_name='timing_histo.pk'

integral_width=7
shift=0
n_samples=50
estimated_gain=20
adc_min=-10
adc_max=3000

mkdir -p $ghv_on_folder $ghv_off_folder $dark_folder $timing_folder $fmpe_folder $baseline_shift_folder $mpe_folder $fmpe_folder$figure_folder_name


#digicam-raw --compute --output=$ghv_off_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1292..1299}.fits.fz
#digicam-raw --display --output=$ghv_off_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1292..1299}.fits.fz
#digicam-raw --compute --output=$ghv_on_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1286..1292}.fits.fz
#digicam-raw --display --output=$ghv_on_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1286..1292}.fits.fz
#digicam-raw --compute --output=$dark_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1276..1279}.fits.fz
#digicam-raw --display --output=$dark_folder$raw_histo_name /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1276..1279}.fits.fz

# digicam-spe --compute --max_histo_filename=$dark_folder$max_histo_name --charge_histo_filename=$dark_folder$charge_histo_name --raw_histo_filename=$dark_folder$raw_histo_name --output=$dark_folder$results_name --integral_width=$integral_width --shift=$shift --n_samples=$n_samples /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1276..1279}.fits.fz
# digicam-spe --fit --max_histo_filename=$dark_folder$max_histo_name --charge_histo_filename=$dark_folder$charge_histo_name --raw_histo_filename=$dark_folder$raw_histo_name --output=$dark_folder$results_name --integral_width=$integral_width --shift=$shift --n_samples=$n_samples /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1276..1279}.fits.fz
# digicam-spe --display --max_histo_filename=$dark_folder$max_histo_name --charge_histo_filename=$dark_folder$charge_histo_name --raw_histo_filename=$dark_folder$raw_histo_name --output=$dark_folder$results_name --integral_width=$integral_width --shift=$shift --n_samples=$n_samples /sst1m/raw/2018/06/27/SST1M_01/SST1M_01_20180627_{1276..1279}.fits.fz

# digicam-timing --compute --timing_histo_filename=$timing_folder$timing_histo_name --n_samples=$n_samples --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-timing --fit --timing_histo_filename=$timing_folder$timing_histo_name --n_samples=$n_samples --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-timing --display --timing_histo_filename=$timing_folder$timing_histo_name --n_samples=$n_samples --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-fmpe --compute --output=$fmpe_folder --estimated_gain=$estimated_gain --n_samples=$n_samples --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing.npz' /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-fmpe --fit --output=$fmpe_folder --estimated_gain=$estimated_gain --n_samples=$n_samples --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing.npz' /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-fmpe --display --output=$fmpe_folder --estimated_gain=$estimated_gain --n_samples=$n_samples --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing_results.npz' /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-fmpe --save_figures --output=$fmpe_folder --estimated_gain=$estimated_gain --n_samples=$n_samples --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing.npz' /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz

# digicam-mpe --compute --output=$mpe_folder --shift=$shift --integral_width=$integral_width --timing=$timing_folder$'timing.npz' --gain=$fmpe_folder'fmpe_fit_results.fits' --adc_min=$adc_min --adc_max=$adc_max --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
digicam-mpe --fit --output=$mpe_folder --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing.npz' --gain=$fmpe_folder'fmpe_fit_results.fits' --adc_min=$adc_min --adc_max=$adc_max --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-mpe --display --output=$mpe_folder --shift=$shift --integral_width=$integral_width --timing=$timing_folder'timing_results.npz' --gain=$fmpe_folder'fmpe_fit_results.npz' --adc_min=$adc_min --adc_max=$adc_max --ac_levels=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,25,30,35,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145,150,155,160,165,170,175,180,185,190,195,200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1350..1454}.fits.fz
# digicam-baseline-shift --compute --output=$baseline_shift_folder --dc_levels=200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1455..1504}.fits.fz
# digicam-baseline-shift --fit --output=$baseline_shift_folder --dc_levels=200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1455..1504}.fits.fz
# digicam-baseline-shift --display --output=$baseline_shift_folder --dc_levels=200,205,210,215,220,225,230,235,240,245,250,255,260,265,270,275,280,285,290,295,300,305,310,315,320,325,330,335,340,345,350,355,360,365,370,375,380,385,390,395,400,405,410,415,420,425,430,435,440,445 /sst1m/raw/2018/06/28/SST1M_01/SST1M_01_20180628_{1455..1504}.fits.fz
