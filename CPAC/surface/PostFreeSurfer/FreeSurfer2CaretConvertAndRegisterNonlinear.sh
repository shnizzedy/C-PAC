#!/bin/bash

# Human Connectome Project [Pipelines][Pipelines] = THIS SOFTWARE

# Copyright (c) 2011-2014 [The Human Connectome Project][HCP]

# Redistribution and use in source and binary forms, with or without modification,
# is permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions, and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions, and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.

# * The names of Washington University in St. Louis, the University of Minnesota,
#   Oxford University, the Human Connectome Project, or any contributors
#   to this software may *not* be used to endorse or promote products derived
#   from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# <!-- References -->

# [HCP]: http://www.humanconnectome.org
# [Pipelines]: https://github.com/Washington-University/Pipelines

# Source: https://github.com/DCAN-Labs/DCAN-HCP/blob/32254dc/PostFreeSurfer/scripts/FreeSurfer2CaretConvertAndRegisterNonlinear.sh

# Modifications copyright (C) 2021 - 2024  C-PAC Developers
# This file is part of C-PAC.

# set -e # If any commands exit with non-zero value, this script exits

# ------------------------------------------------------------------------------
#  Verify HCPPIPEDIR environment variable is set
# ------------------------------------------------------------------------------

# if [ -z "${HCPPIPEDIR}" ]; then
# 	script_name=$(basename "${0}")
# 	echo "${script_name}: ABORTING: HCPPIPEDIR environment variable must be set"
# 	exit 1
# fi

# ------------------------------------------------------------------------------
#  Load function libraries
# ------------------------------------------------------------------------------

HCPPIPEDIR=/code/CPAC/resources
source ${HCPPIPEDIR}/global/scripts/log.shlib # Logging related functions
echo "HCPPIPEDIR: ${HCPPIPEDIR}"

# ------------------------------------------------------------------------------
#  Verify other needed environment variables are set
# ------------------------------------------------------------------------------

# if [ -z "${MSMBINDIR}" ]; then
# 	log_Err_Abort "MSMBINDIR environment variable must be set"
# fi
# echo "MSMBINDIR: ${MSMBINDIR}" # /opt/msm/Ubuntu

# if [ -z "${MSMCONFIGDIR}" ]; then
# 	log_Err_Abort "MSMCONFIGDIR environment variable must be set"
# fi
# echo "MSMCONFIGDIR: ${MSMCONFIGDIR}" # /opt/pipeline/MSMConfig

MSMCONFIGDIR=${HCPPIPEDIR}/MSMConfig

# if [ -z "${CARET7DIR}" ]; then
# 	log_Err_Abort "CARET7DIR environment variable must be set"
# fi
# echo "CARET7DIR: ${CARET7DIR}"

# ------------------------------------------------------------------------------
#  Gather and show positional parameters
# ------------------------------------------------------------------------------

echo "START"

StudyFolder="$1"
echo "StudyFolder: ${StudyFolder}"

Subject="$2"
echo "Subject: ${Subject}"

T1wFolder="$3"
echo "T1wFolder: ${T1wFolder}"

AtlasSpaceFolder="$4"
echo "AtlasSpaceFolder: ${AtlasSpaceFolder}"

NativeFolder="$5"
echo "NativeFolder: ${NativeFolder}"

FreeSurferFolder="$6"
echo "FreeSurferFolder: ${FreeSurferFolder}"

FreeSurferInput="$7"
echo "FreeSurferInput: ${FreeSurferInput}"

T1wImage="$8"
echo "T1wImage: ${T1wImage}"

T2wImage="$9"
echo "T2wImage: ${T2wImage}"

SurfaceAtlasDIR="${10}"
echo "SurfaceAtlasDIR: ${SurfaceAtlasDIR}"

HighResMesh="${11}"
echo "HighResMesh: ${HighResMesh}"

LowResMeshes="${12}"
echo "LowResMeshes: ${LowResMeshes}"

AtlasTransform="${13}"
echo "AtlasTransform: ${AtlasTransform}"

InverseAtlasTransform="${14}"
echo "InverseAtlasTransform: ${InverseAtlasTransform}"

AtlasSpaceT1wImage="${15}"
echo "AtlasSpaceT1wImage: ${AtlasSpaceT1wImage}"

AtlasSpaceT2wImage="${16}"
echo "AtlasSpaceT2wImage: ${AtlasSpaceT2wImage}"

T1wImageBrainMask="${17}"
echo "T1wImageBrainMask: ${T1wImageBrainMask}"

FreeSurferLabels="${18}"
echo "FreeSurferLabels: ${FreeSurferLabels}"

GrayordinatesSpaceDIR="${19}"
echo "GrayordinatesSpaceDIR: ${GrayordinatesSpaceDIR}"

GrayordinatesResolutions="${20}"
echo "GrayordinatesResolutions: ${GrayordinatesResolutions}"

SubcorticalGrayLabels="${21}"
echo "SubcorticalGrayLabels: ${SubcorticalGrayLabels}"

RegName="${22}"
echo "RegName: ${RegName}"

InflateExtraScale="${23}"
echo "InflateExtraScale: ${InflateExtraScale}"

useT2="${24}"
echo "useT2: ${useT2}"

LowResMeshes=${LowResMeshes//@/ }
echo "LowResMeshes: ${LowResMeshes}"

GrayordinatesResolutions=${GrayordinatesResolutions//@/ }
echo "GrayordinatesResolutions: ${GrayordinatesResolutions}"

#Make some folders for this and later scripts
if [ ! -e "$T1wFolder"/"$NativeFolder" ] ; then
	mkdir -p "$T1wFolder"/"$NativeFolder"
fi
if [ ! -e "$AtlasSpaceFolder"/ROIs ] ; then
	mkdir -p "$AtlasSpaceFolder"/ROIs
fi
if [ ! -e "$AtlasSpaceFolder"/Results ] ; then
	mkdir "$AtlasSpaceFolder"/Results
fi
if [ ! -e "$AtlasSpaceFolder"/"$NativeFolder" ] ; then
	mkdir "$AtlasSpaceFolder"/"$NativeFolder"
fi
if [ ! -e "$AtlasSpaceFolder"/fsaverage ] ; then
	mkdir "$AtlasSpaceFolder"/fsaverage
fi
for LowResMesh in ${LowResMeshes} ; do
	if [ ! -e "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k ] ; then
		mkdir "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k
	fi
	if [ ! -e "$T1wFolder"/fsaverage_LR"$LowResMesh"k ] ; then
		mkdir "$T1wFolder"/fsaverage_LR"$LowResMesh"k
	fi
done

#Find c_ras offset between FreeSurfer surface and volume and generate matrix to transform surfaces
# MatrixX=$(mri_info "$FreeSurferFolder"/mri/brain.finalsurfs.mgz | grep "c_r" | head -n 1 | cut -d "=" -f 5 | sed s/" "/""/g)
# MatrixY=$(mri_info "$FreeSurferFolder"/mri/brain.finalsurfs.mgz | grep "c_a" | head -n 1 | cut -d "=" -f 5 | sed s/" "/""/g)
# MatrixZ=$(mri_info "$FreeSurferFolder"/mri/brain.finalsurfs.mgz | grep "c_s" | head -n 1 | cut -d "=" -f 5 | sed s/" "/""/g)
# echo "1 0 0 ""$MatrixX" >> "$FreeSurferFolder"/mri/c_ras.mat
# echo "0 1 0 ""$MatrixY" >> "$FreeSurferFolder"/mri/c_ras.mat
# echo "0 0 1 ""$MatrixZ" >> "$FreeSurferFolder"/mri/c_ras.mat
# echo "0 0 0 1" >> "$FreeSurferFolder"/mri/c_ras.mat

cd ${FreeSurferFolder}
rm mri/c_ras.mat
MatrixX=$(mri_info mri/brain.finalsurfs.mgz | grep "c_r" | cut -d "=" -f 5 | sed s/" "/""/g)
MatrixY=$(mri_info mri/brain.finalsurfs.mgz | grep "c_a" | cut -d "=" -f 5 | sed s/" "/""/g)
MatrixZ=$(mri_info mri/brain.finalsurfs.mgz | grep "c_s" | cut -d "=" -f 5 | sed s/" "/""/g)
echo "1 0 0 ""$MatrixX" >> mri/c_ras.mat
echo "0 1 0 ""$MatrixY" >> mri/c_ras.mat
echo "0 0 1 ""$MatrixZ" >> mri/c_ras.mat
echo "0 0 0 1" >> mri/c_ras.mat
cd ${StudyFolder}

#Convert FreeSurfer Volumes
for Image in wmparc aparc.a2009s+aseg aparc+aseg ; do
	if [ -e "$FreeSurferFolder"/mri/"$Image".mgz ] ; then

		mri_convert -rt nearest -rl "$T1wFolder"/"$T1wImage".nii.gz "$FreeSurferFolder"/mri/"$Image".mgz "$T1wFolder"/"$Image"_1mm.nii.gz
		applywarp --rel --interp=nn -i "$T1wFolder"/"$Image"_1mm.nii.gz -r "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage" --premat=$FSLDIR/etc/flirtsch/ident.mat -o "$T1wFolder"/"$Image".nii.gz
		applywarp --rel --interp=nn -i "$T1wFolder"/"$Image"_1mm.nii.gz -r "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage" -w "$AtlasTransform" -o "$AtlasSpaceFolder"/"$Image".nii.gz
		wb_command -volume-label-import "$T1wFolder"/"$Image".nii.gz "$FreeSurferLabels" "$T1wFolder"/"$Image".nii.gz -drop-unused-labels
		wb_command -volume-label-import "$AtlasSpaceFolder"/"$Image".nii.gz "$FreeSurferLabels" "$AtlasSpaceFolder"/"$Image".nii.gz -drop-unused-labels
	fi
done

#Create FreeSurfer Brain Mask (Now done in PostFreeSurfer.sh so brainmask_fs.nii.gz exists for ANTs Registration)
fslmaths "$T1wFolder"/wmparc_1mm.nii.gz -bin -dilD -dilD -dilD -ero -ero "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz
wb_command -volume-fill-holes "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz
fslmaths "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz -bin "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz
applywarp --rel --interp=nn -i "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz -r "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage" --premat=$FSLDIR/etc/flirtsch/ident.mat -o "$T1wFolder"/"$T1wImageBrainMask".nii.gz
applywarp --rel --interp=nn -i "$T1wFolder"/"$T1wImageBrainMask"_1mm.nii.gz -r "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage" -w "$AtlasTransform" -o "$AtlasSpaceFolder"/"$T1wImageBrainMask".nii.gz

#Add volume files to spec files
if $useT2; then
wb_command -add-to-spec-file "$T1wFolder"/"$NativeFolder"/"$Subject".native.wb.spec INVALID "$T1wFolder"/"$T2wImage".nii.gz
fi
wb_command -add-to-spec-file "$T1wFolder"/"$NativeFolder"/"$Subject".native.wb.spec INVALID "$T1wFolder"/"$T1wImage".nii.gz

if $useT2; then
wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject".native.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT2wImage".nii.gz
fi
wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject".native.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage".nii.gz

if $useT2; then
wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT2wImage".nii.gz
fi
wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage".nii.gz

for LowResMesh in ${LowResMeshes} ; do
  if $useT2; then
  wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT2wImage".nii.gz
  fi
  wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec INVALID "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage".nii.gz

  if $useT2; then
  wb_command -add-to-spec-file "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec INVALID "$T1wFolder"/"$T2wImage".nii.gz
  fi
  wb_command -add-to-spec-file "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec INVALID "$T1wFolder"/"$T1wImage".nii.gz
done

#Import Subcortical ROIs
for GrayordinatesResolution in ${GrayordinatesResolutions} ; do
  cp "$GrayordinatesSpaceDIR"/Atlas_ROIs."$GrayordinatesResolution".nii.gz "$AtlasSpaceFolder"/ROIs/Atlas_ROIs."$GrayordinatesResolution".nii.gz
  applywarp --interp=nn -i "$AtlasSpaceFolder"/wmparc.nii.gz -r "$AtlasSpaceFolder"/ROIs/Atlas_ROIs."$GrayordinatesResolution".nii.gz -o "$AtlasSpaceFolder"/ROIs/wmparc."$GrayordinatesResolution".nii.gz
  wb_command -volume-label-import "$AtlasSpaceFolder"/ROIs/wmparc."$GrayordinatesResolution".nii.gz "$FreeSurferLabels" "$AtlasSpaceFolder"/ROIs/wmparc."$GrayordinatesResolution".nii.gz -drop-unused-labels
  applywarp --interp=nn -i "$SurfaceAtlasDIR"/Avgwmparc.nii.gz -r "$AtlasSpaceFolder"/ROIs/Atlas_ROIs."$GrayordinatesResolution".nii.gz -o "$AtlasSpaceFolder"/ROIs/Atlas_wmparc."$GrayordinatesResolution".nii.gz
  wb_command -volume-label-import "$AtlasSpaceFolder"/ROIs/Atlas_wmparc."$GrayordinatesResolution".nii.gz "$FreeSurferLabels" "$AtlasSpaceFolder"/ROIs/Atlas_wmparc."$GrayordinatesResolution".nii.gz -drop-unused-labels
  wb_command -volume-label-import "$AtlasSpaceFolder"/ROIs/wmparc."$GrayordinatesResolution".nii.gz ${SubcorticalGrayLabels} "$AtlasSpaceFolder"/ROIs/ROIs."$GrayordinatesResolution".nii.gz -discard-others
  if $useT2; then
  applywarp --interp=spline -i "$AtlasSpaceFolder"/"$AtlasSpaceT2wImage".nii.gz -r "$AtlasSpaceFolder"/ROIs/Atlas_ROIs."$GrayordinatesResolution".nii.gz -o "$AtlasSpaceFolder"/"$AtlasSpaceT2wImage"."$GrayordinatesResolution".nii.gz
  fi
  applywarp --interp=spline -i "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage".nii.gz -r "$AtlasSpaceFolder"/ROIs/Atlas_ROIs."$GrayordinatesResolution".nii.gz -o "$AtlasSpaceFolder"/"$AtlasSpaceT1wImage"."$GrayordinatesResolution".nii.gz
done

#Loop through left and right hemispheres
for Hemisphere in L R ; do
	#Set a bunch of different ways of saying left and right
	if [ $Hemisphere = "L" ] ; then
		hemisphere="l"
		Structure="CORTEX_LEFT"
	elif [ $Hemisphere = "R" ] ; then
		hemisphere="r"
		Structure="CORTEX_RIGHT"
	fi

	#native Mesh Processing
	#Convert and volumetrically register white and pial surfaces making linear and nonlinear copies, add each to the appropriate spec file
	Types="ANATOMICAL@GRAY_WHITE ANATOMICAL@PIAL"
	i=1
	for Surface in white pial ; do
		Type=$(echo "$Types" | cut -d " " -f $i)
		Secondary=$(echo "$Type" | cut -d "@" -f 2)
		Type=$(echo "$Type" | cut -d "@" -f 1)
		if [ ! $Secondary = $Type ] ; then
			Secondary=$(echo " -surface-secondary-type ""$Secondary")
		else
			Secondary=""
		fi
		mris_convert "$FreeSurferFolder"/surf/"$hemisphere"h."$Surface" "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii
		wb_command -set-structure "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii ${Structure} -surface-type $Type$Secondary
		wb_command -surface-apply-affine "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii "$FreeSurferFolder"/mri/c_ras.mat "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii
		wb_command -add-to-spec-file "$T1wFolder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii
		wb_command -surface-apply-warpfield "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii "$InverseAtlasTransform".nii.gz "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii -fnirt "$AtlasTransform".nii.gz
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii
		i=$(( i+1 ))
	done

	#Create midthickness by averaging white and pial surfaces and use it to make inflated surfacess
	for Folder in "$T1wFolder" "$AtlasSpaceFolder" ; do
		wb_command -surface-average "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii -surf "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".white.native.surf.gii -surf "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".pial.native.surf.gii
		wb_command -set-structure "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii ${Structure} -surface-type ANATOMICAL -surface-secondary-type MIDTHICKNESS
		wb_command -add-to-spec-file "$Folder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii

		#get number of vertices from native file
		NativeVerts=$(wb_command -file-information "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii | grep 'Number of Vertices:' | cut -f2 -d: | tr -d '[:space:]')

		#HCP fsaverage_LR32k used -iterations-scale 0.75. Compute new param value for native mesh density
		NativeInflationScale=$(echo "scale=4; $InflateExtraScale * 0.75 * $NativeVerts / 32492" | bc -l)

		wb_command -surface-generate-inflated "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".inflated.native.surf.gii "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".very_inflated.native.surf.gii -iterations-scale $NativeInflationScale
		wb_command -add-to-spec-file "$Folder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".inflated.native.surf.gii
		wb_command -add-to-spec-file "$Folder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$Folder"/"$NativeFolder"/"$Subject"."$Hemisphere".very_inflated.native.surf.gii
	done

	#Convert original and registered spherical surfaces and add them to the nonlinear spec file
	for Surface in sphere.reg sphere ; do
		mris_convert "$FreeSurferFolder"/surf/"$hemisphere"h."$Surface" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii
		wb_command -set-structure "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii ${Structure} -surface-type SPHERICAL
	done
	wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject".native.wb.spec $Structure "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii

	#Add more files to the spec file and convert other FreeSurfer surface data to metric/GIFTI including sulc, curv, and thickness.
	for Map in sulc@sulc@Sulc thickness@thickness@Thickness curv@curvature@Curvature ; do
		fsname=$(echo $Map | cut -d "@" -f 1)
		wbname=$(echo $Map | cut -d "@" -f 2)
		mapname=$(echo $Map | cut -d "@" -f 3)
		mris_convert -c "$FreeSurferFolder"/surf/"$hemisphere"h."$fsname" "$FreeSurferFolder"/surf/"$hemisphere"h.white "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii
		wb_command -set-structure "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii ${Structure}
		wb_command -metric-math "var * -1" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii -var var "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii
		wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii -map 1 "$Subject"_"$Hemisphere"_"$mapname"
		wb_command -metric-palette "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$wbname".native.shape.gii MODE_AUTO_SCALE_PERCENTAGE -pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true
	done
	#Thickness specific operations
	wb_command -metric-math "abs(thickness)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii -var thickness "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii
	wb_command -metric-palette "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii MODE_AUTO_SCALE_PERCENTAGE -pos-percent 4 96 -interpolate true -palette-name videen_style -disp-pos true -disp-neg false -disp-zero false
	wb_command -metric-math "thickness > 0" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii -var thickness "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii
	wb_command -metric-fill-holes "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii
	wb_command -metric-remove-islands "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii
	wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii -map 1 "$Subject"_"$Hemisphere"_ROI
	wb_command -metric-dilate "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii 10 "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii -nearest
	wb_command -metric-dilate "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".curvature.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii 10 "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".curvature.native.shape.gii -nearest

	#Label operations
	for Map in aparc aparc.a2009s ; do #Remove BA because it doesn't convert properly
		if [ -e "$FreeSurferFolder"/label/"$hemisphere"h."$Map".annot ] ; then
			mris_convert --annot "$FreeSurferFolder"/label/"$hemisphere"h."$Map".annot "$FreeSurferFolder"/surf/"$hemisphere"h.white "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii
			wb_command -set-structure "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii $Structure
			wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii -map 1 "$Subject"_"$Hemisphere"_"$Map"
			wb_command -gifti-label-add-prefix "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii "${Hemisphere}_" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii
		fi
	done
	#End main native mesh processing

	#Copy Atlas Files
	cp "$SurfaceAtlasDIR"/fs_"$Hemisphere"/fsaverage."$Hemisphere".sphere."$HighResMesh"k_fs_"$Hemisphere".surf.gii "$AtlasSpaceFolder"/fsaverage/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_"$Hemisphere".surf.gii
	cp "$SurfaceAtlasDIR"/fs_"$Hemisphere"/fs_"$Hemisphere"-to-fs_LR_fsaverage."$Hemisphere"_LR.spherical_std."$HighResMesh"k_fs_"$Hemisphere".surf.gii "$AtlasSpaceFolder"/fsaverage/"$Subject"."$Hemisphere".def_sphere."$HighResMesh"k_fs_"$Hemisphere".surf.gii
	cp "$SurfaceAtlasDIR"/fsaverage."$Hemisphere"_LR.spherical_std."$HighResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii
	wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii
	cp "$SurfaceAtlasDIR"/"$Hemisphere".atlasroi."$HighResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".atlasroi."$HighResMesh"k_fs_LR.shape.gii
	cp "$SurfaceAtlasDIR"/"$Hemisphere".refsulc."$HighResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/${Subject}.${Hemisphere}.refsulc."$HighResMesh"k_fs_LR.shape.gii
	if [ -e "$SurfaceAtlasDIR"/colin.cerebral."$Hemisphere".flat."$HighResMesh"k_fs_LR.surf.gii ] ; then
		cp "$SurfaceAtlasDIR"/colin.cerebral."$Hemisphere".flat."$HighResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".flat."$HighResMesh"k_fs_LR.surf.gii
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".flat."$HighResMesh"k_fs_LR.surf.gii
	fi

	#Concatenate FS registration to FS --> FS_LR registration
	wb_command -surface-sphere-project-unproject "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.native.surf.gii "$AtlasSpaceFolder"/fsaverage/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_"$Hemisphere".surf.gii "$AtlasSpaceFolder"/fsaverage/"$Subject"."$Hemisphere".def_sphere."$HighResMesh"k_fs_"$Hemisphere".surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.surf.gii

	#Make FreeSurfer Registration Areal Distortion Maps
	wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii
	wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.shape.gii
	wb_command -metric-math "ln(spherereg / sphere) / ln(2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS.native.shape.gii -var sphere "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii -var spherereg "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.shape.gii
	rm "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.shape.gii
	wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS.native.shape.gii -map 1 "$Subject"_"$Hemisphere"_Areal_Distortion_FS
	wb_command -metric-palette "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS.native.shape.gii MODE_AUTO_SCALE -palette-name ROY-BIG-BL -thresholding THRESHOLD_TYPE_NORMAL THRESHOLD_TEST_SHOW_OUTSIDE -1 1

	wb_command -surface-distortion "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_FS.native.shape.gii -edge-method

  wb_command -surface-distortion "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.reg.reg_LR.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_FS.native.shape.gii -local-affine-method
  wb_command -metric-merge "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_FS.native.shape.gii -metric "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_FS.native.shape.gii -column 1
  wb_command -metric-merge "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_FS.native.shape.gii -metric "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_FS.native.shape.gii -column 2
  wb_command -metric-math "ln(var) / ln (2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_FS.native.shape.gii -var var "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_FS.native.shape.gii
  wb_command -metric-math "ln(var) / ln (2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_FS.native.shape.gii -var var "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_FS.native.shape.gii
  rm "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_FS.native.shape.gii

	#If desired, run MSMSulc folding-based registration to FS_LR initialized with FS affine
	if [ ${RegName} = "MSMSulc" ] ; then
		#Calculate Affine Transform and Apply
		if [ ! -e "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc ] ; then
		  mkdir "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc
		fi
		wb_command -surface-affine-regression "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.reg.reg_LR.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.mat
		wb_command -surface-apply-affine "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.mat "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii
		wb_command -surface-modify-sphere "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii 100 "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii
		cp "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere_rot.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii
		DIR=$(pwd)
		cd "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc
		#Register using FreeSurfer Sulc Folding Map Using MSM Algorithm Configured for Reduced Distortion
		#msm --version
		#msm --levels=4 --conf=${MSMCONFIGDIR}/allparameterssulcDRconf --inmesh="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii --trans="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii --refmesh="$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii --indata="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sulc.native.shape.gii --refdata="$AtlasSpaceFolder"/${Subject}.${Hemisphere}.refsulc."$HighResMesh"k_fs_LR.shape.gii --out="$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}. --verbose
		# Note: the config is mordified according to acceptable args of msm version in container - XL
		msm --conf=${MSMCONFIGDIR}/MSMSulcStrainFinalconf --inmesh="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.rot.native.surf.gii --refmesh="$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii --indata="$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sulc.native.shape.gii --refdata="$AtlasSpaceFolder"/${Subject}.${Hemisphere}.refsulc."$HighResMesh"k_fs_LR.shape.gii --out="$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}. --verbose
    cp ${MSMCONFIGDIR}/MSMSulcStrainFinalconf "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.logdir/conf
		cd $DIR
		#cp "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.HIGHRES_transformed.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii
		cp "$AtlasSpaceFolder"/"$NativeFolder"/MSMSulc/${Hemisphere}.sphere.reg.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii
		wb_command -set-structure "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii ${Structure}

		#Make MSMSulc Registration Areal Distortion Maps
		wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii
		wb_command -surface-vertex-areas "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
		wb_command -metric-math "ln(spherereg / sphere) / ln(2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii -var sphere "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii -var spherereg "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
		rm "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/${Subject}.${Hemisphere}.sphere.MSMSulc.native.shape.gii
		wb_command -set-map-names "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii -map 1 "$Subject"_"$Hemisphere"_Areal_Distortion_MSMSulc
		wb_command -metric-palette "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii MODE_AUTO_SCALE -palette-name ROY-BIG-BL -thresholding THRESHOLD_TYPE_NORMAL THRESHOLD_TEST_SHOW_OUTSIDE -1 1

		wb_command -surface-distortion "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.MSMSulc.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_MSMSulc.native.shape.gii -edge-method

    wb_command -surface-distortion "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sphere.MSMSulc.native.surf.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_MSMSulc.native.shape.gii -local-affine-method
    wb_command -metric-merge "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc.native.shape.gii -metric "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_MSMSulc.native.shape.gii -column 1
    wb_command -metric-merge "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc.native.shape.gii -metric "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_MSMSulc.native.shape.gii -column 2
    wb_command -metric-math "ln(var) / ln (2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc.native.shape.gii -var var "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc.native.shape.gii
    wb_command -metric-math "ln(var) / ln (2)" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc.native.shape.gii -var var "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc.native.shape.gii
    rm "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".Strain_MSMSulc.native.shape.gii

		RegSphere="${AtlasSpaceFolder}/${NativeFolder}/${Subject}.${Hemisphere}.sphere.MSMSulc.native.surf.gii"
	else
		RegSphere="${AtlasSpaceFolder}/${NativeFolder}/${Subject}.${Hemisphere}.sphere.reg.reg_LR.native.surf.gii"
	fi

	#Ensure no zeros in atlas medial wall ROI
	wb_command -metric-resample "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".atlasroi."$HighResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ${RegSphere} BARYCENTRIC "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".atlasroi.native.shape.gii -largest
	wb_command -metric-math "(atlas + individual) > 0" "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii -var atlas "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".atlasroi.native.shape.gii -var individual "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii
	wb_command -metric-mask "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".thickness.native.shape.gii
	wb_command -metric-mask "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".curvature.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".curvature.native.shape.gii


	#Populate Highres fs_LR spec file.  Deform surfaces and other data according to native to folding-based registration selected above.  Regenerate inflated surfaces.
	for Surface in white midthickness pial ; do
		wb_command -surface-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii BARYCENTRIC "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Surface"."$HighResMesh"k_fs_LR.surf.gii
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Surface"."$HighResMesh"k_fs_LR.surf.gii
	done

	#HCP fsaverage_LR32k used -iterations-scale 0.75. Compute new param value for high res mesh density
	HighResInflationScale=$(echo "scale=4; $InflateExtraScale * 0.75 * $HighResMesh / 32" | bc -l)

	wb_command -surface-generate-inflated "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".inflated."$HighResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".very_inflated."$HighResMesh"k_fs_LR.surf.gii -iterations-scale $HighResInflationScale
	wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".inflated."$HighResMesh"k_fs_LR.surf.gii
	wb_command -add-to-spec-file "$AtlasSpaceFolder"/"$Subject"."$HighResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".very_inflated."$HighResMesh"k_fs_LR.surf.gii

	for Map in thickness curvature ; do
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Map"."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii -current-roi "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii
		wb_command -metric-mask "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Map"."$HighResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".atlasroi."$HighResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Map"."$HighResMesh"k_fs_LR.shape.gii
	done
	wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
	wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".EdgeDistortion_FS."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
	wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".StrainJ_FS."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
	wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".StrainR_FS."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
	if [ ${RegName} = "MSMSulc" ] ; then
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".EdgeDistortion_MSMSulc."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii
	fi
	wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sulc."$HighResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".midthickness."$HighResMesh"k_fs_LR.surf.gii

	for Map in aparc aparc.a2009s ; do #Remove BA because it doesn't convert properly
		if [ -e "$FreeSurferFolder"/label/"$hemisphere"h."$Map".annot ] ; then
			wb_command -label-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii ${RegSphere} "$AtlasSpaceFolder"/"$Subject"."$Hemisphere".sphere."$HighResMesh"k_fs_LR.surf.gii BARYCENTRIC "$AtlasSpaceFolder"/"$Subject"."$Hemisphere"."$Map"."$HighResMesh"k_fs_LR.label.gii -largest
		fi
	done

	for LowResMesh in ${LowResMeshes} ; do
		#Copy Atlas Files
		cp "$SurfaceAtlasDIR"/"$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii
		cp "$GrayordinatesSpaceDIR"/"$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.shape.gii
		if [ -e "$SurfaceAtlasDIR"/colin.cerebral."$Hemisphere".flat."$LowResMesh"k_fs_LR.surf.gii ] ; then
			cp "$SurfaceAtlasDIR"/colin.cerebral."$Hemisphere".flat."$LowResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".flat."$LowResMesh"k_fs_LR.surf.gii
			wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".flat."$LowResMesh"k_fs_LR.surf.gii
		fi

		#Create downsampled fs_LR spec files.
		for Surface in white midthickness pial ; do
			wb_command -surface-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii BARYCENTRIC "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Surface"."$LowResMesh"k_fs_LR.surf.gii
			wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Surface"."$LowResMesh"k_fs_LR.surf.gii
		done

		#HCP fsaverage_LR32k used -iterations-scale 0.75. Recalculate in case using a different mesh
		LowResInflationScale=$(echo "scale=4; $InflateExtraScale * 0.75 * $LowResMesh / 32" | bc -l)

		wb_command -surface-generate-inflated "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".inflated."$LowResMesh"k_fs_LR.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".very_inflated."$LowResMesh"k_fs_LR.surf.gii -iterations-scale "$LowResInflationScale"
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".inflated."$LowResMesh"k_fs_LR.surf.gii
		wb_command -add-to-spec-file "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".very_inflated."$LowResMesh"k_fs_LR.surf.gii

		for Map in sulc thickness curvature ; do
			wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Map"."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii -current-roi "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".roi.native.shape.gii
			wb_command -metric-mask "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Map"."$LowResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".atlasroi."$LowResMesh"k_fs_LR.shape.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Map"."$LowResMesh"k_fs_LR.shape.gii
		done
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".ArealDistortion_FS."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".EdgeDistortion_FS."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".StrainJ_FS."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_FS.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".StrainR_FS."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
		if [ ${RegName} = "MSMSulc" ] ; then
			wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".ArealDistortion_MSMSulc."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
			wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".EdgeDistortion_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".EdgeDistortion_MSMSulc."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
			wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainJ_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".StrainJ_MSMSulc."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
			wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".StrainR_MSMSulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".StrainR_MSMSulc."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii
		fi
		wb_command -metric-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".sulc.native.shape.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii ADAP_BARY_AREA "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sulc."$LowResMesh"k_fs_LR.shape.gii -area-surfs "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere".midthickness.native.surf.gii "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii

		for Map in aparc aparc.a2009s ; do #Remove BA because it doesn't convert properly
			if [ -e "$FreeSurferFolder"/label/"$hemisphere"h."$Map".annot ] ; then
				wb_command -label-resample "$AtlasSpaceFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Map".native.label.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii BARYCENTRIC "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Map"."$LowResMesh"k_fs_LR.label.gii -largest
			fi
		done

		#Create downsampled fs_LR spec file in structural space.
		for Surface in white midthickness pial ; do
			wb_command -surface-resample "$T1wFolder"/"$NativeFolder"/"$Subject"."$Hemisphere"."$Surface".native.surf.gii ${RegSphere} "$AtlasSpaceFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".sphere."$LowResMesh"k_fs_LR.surf.gii BARYCENTRIC "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Surface"."$LowResMesh"k_fs_LR.surf.gii
			wb_command -add-to-spec-file "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere"."$Surface"."$LowResMesh"k_fs_LR.surf.gii
		done

		#HCP fsaverage_LR32k used -iterations-scale 0.75. Recalculate in case using a different mesh
		LowResInflationScale=$(echo "scale=4; $InflateExtraScale * 0.75 * $LowResMesh / 32" | bc -l)

		wb_command -surface-generate-inflated "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".midthickness."$LowResMesh"k_fs_LR.surf.gii "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".inflated."$LowResMesh"k_fs_LR.surf.gii "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".very_inflated."$LowResMesh"k_fs_LR.surf.gii -iterations-scale "$LowResInflationScale"
		wb_command -add-to-spec-file "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".inflated."$LowResMesh"k_fs_LR.surf.gii
		wb_command -add-to-spec-file "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$LowResMesh"k_fs_LR.wb.spec $Structure "$T1wFolder"/fsaverage_LR"$LowResMesh"k/"$Subject"."$Hemisphere".very_inflated."$LowResMesh"k_fs_LR.surf.gii
	done
done

STRINGII=""
for LowResMesh in ${LowResMeshes} ; do
	STRINGII=$(echo "${STRINGII}${AtlasSpaceFolder}/fsaverage_LR${LowResMesh}k@${LowResMesh}k_fs_LR@atlasroi ")
done

#Create CIFTI Files
for STRING in "$AtlasSpaceFolder"/"$NativeFolder"@native@roi "$AtlasSpaceFolder"@"$HighResMesh"k_fs_LR@atlasroi ${STRINGII} ; do
	Folder=$(echo $STRING | cut -d "@" -f 1)
	Mesh=$(echo $STRING | cut -d "@" -f 2)
	ROI=$(echo $STRING | cut -d "@" -f 3)

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".sulc."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.sulc."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.sulc."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".sulc."$Mesh".dscalar.nii -map 1 "${Subject}_Sulc"
	wb_command -cifti-palette "$Folder"/"$Subject".sulc."$Mesh".dscalar.nii MODE_AUTO_SCALE_PERCENTAGE "$Folder"/"$Subject".sulc."$Mesh".dscalar.nii -pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".curvature."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.curvature."$Mesh".shape.gii -roi-left "$Folder"/"$Subject".L."$ROI"."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.curvature."$Mesh".shape.gii -roi-right "$Folder"/"$Subject".R."$ROI"."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".curvature."$Mesh".dscalar.nii -map 1 "${Subject}_Curvature"
	wb_command -cifti-palette "$Folder"/"$Subject".curvature."$Mesh".dscalar.nii MODE_AUTO_SCALE_PERCENTAGE "$Folder"/"$Subject".curvature."$Mesh".dscalar.nii -pos-percent 2 98 -palette-name Gray_Interp -disp-pos true -disp-neg true -disp-zero true

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".thickness."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.thickness."$Mesh".shape.gii -roi-left "$Folder"/"$Subject".L."$ROI"."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.thickness."$Mesh".shape.gii -roi-right "$Folder"/"$Subject".R."$ROI"."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".thickness."$Mesh".dscalar.nii -map 1 "${Subject}_Thickness"
	wb_command -cifti-palette "$Folder"/"$Subject".thickness."$Mesh".dscalar.nii MODE_AUTO_SCALE_PERCENTAGE "$Folder"/"$Subject".thickness."$Mesh".dscalar.nii -pos-percent 4 96 -interpolate true -palette-name videen_style -disp-pos true -disp-neg false -disp-zero false

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".ArealDistortion_FS."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.ArealDistortion_FS."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.ArealDistortion_FS."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".ArealDistortion_FS."$Mesh".dscalar.nii -map 1 "${Subject}_ArealDistortion_FS"
	wb_command -cifti-palette "$Folder"/"$Subject".ArealDistortion_FS."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".ArealDistortion_FS."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".EdgeDistortion_FS."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.EdgeDistortion_FS."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.EdgeDistortion_FS."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".EdgeDistortion_FS."$Mesh".dscalar.nii -map 1 "${Subject}_EdgeDistortion_FS"
	wb_command -cifti-palette "$Folder"/"$Subject".EdgeDistortion_FS."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".EdgeDistortion_FS."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".StrainJ_FS."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.StrainJ_FS."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.StrainJ_FS."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".StrainJ_FS."$Mesh".dscalar.nii -map 1 "${Subject}_StrainJ_FS"
	wb_command -cifti-palette "$Folder"/"$Subject".StrainJ_FS."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".StrainJ_FS."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

	wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".StrainR_FS."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.StrainR_FS."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.StrainR_FS."$Mesh".shape.gii
	wb_command -set-map-names "$Folder"/"$Subject".StrainR_FS."$Mesh".dscalar.nii -map 1 "${Subject}_StrainR_FS"
	wb_command -cifti-palette "$Folder"/"$Subject".StrainR_FS."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".StrainR_FS."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

	if [ ${RegName} = "MSMSulc" ] ; then
		wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".ArealDistortion_MSMSulc."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.ArealDistortion_MSMSulc."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.ArealDistortion_MSMSulc."$Mesh".shape.gii
		wb_command -set-map-names "$Folder"/"$Subject".ArealDistortion_MSMSulc."$Mesh".dscalar.nii -map 1 "${Subject}_ArealDistortion_MSMSulc"
		wb_command -cifti-palette "$Folder"/"$Subject".ArealDistortion_MSMSulc."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".ArealDistortion_MSMSulc."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

		wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".EdgeDistortion_MSMSulc."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.EdgeDistortion_MSMSulc."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.EdgeDistortion_MSMSulc."$Mesh".shape.gii
		wb_command -set-map-names "$Folder"/"$Subject".EdgeDistortion_MSMSulc."$Mesh".dscalar.nii -map 1 "${Subject}_EdgeDistortion_MSMSulc"
		wb_command -cifti-palette "$Folder"/"$Subject".EdgeDistortion_MSMSulc."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".EdgeDistortion_MSMSulc."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

		wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".StrainJ_MSMSulc."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.StrainJ_MSMSulc."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.StrainJ_MSMSulc."$Mesh".shape.gii
		wb_command -set-map-names "$Folder"/"$Subject".StrainJ_MSMSulc."$Mesh".dscalar.nii -map 1 "${Subject}_StrainJ_MSMSulc"
		wb_command -cifti-palette "$Folder"/"$Subject".StrainJ_MSMSulc."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".StrainJ_MSMSulc."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false

		wb_command -cifti-create-dense-scalar "$Folder"/"$Subject".StrainR_MSMSulc."$Mesh".dscalar.nii -left-metric "$Folder"/"$Subject".L.StrainR_MSMSulc."$Mesh".shape.gii -right-metric "$Folder"/"$Subject".R.StrainR_MSMSulc."$Mesh".shape.gii
		wb_command -set-map-names "$Folder"/"$Subject".StrainR_MSMSulc."$Mesh".dscalar.nii -map 1 "${Subject}_StrainR_MSMSulc"
		wb_command -cifti-palette "$Folder"/"$Subject".StrainR_MSMSulc."$Mesh".dscalar.nii MODE_USER_SCALE "$Folder"/"$Subject".StrainR_MSMSulc."$Mesh".dscalar.nii -pos-user 0 1 -neg-user 0 -1 -interpolate true -palette-name ROY-BIG-BL -disp-pos true -disp-neg true -disp-zero false
	fi

	for Map in aparc aparc.a2009s ; do #Remove BA because it doesn't convert properly
		if [ -e "$Folder"/"$Subject".L.${Map}."$Mesh".label.gii ] ; then
			wb_command -cifti-create-label "$Folder"/"$Subject".${Map}."$Mesh".dlabel.nii -left-label "$Folder"/"$Subject".L.${Map}."$Mesh".label.gii -roi-left "$Folder"/"$Subject".L."$ROI"."$Mesh".shape.gii -right-label "$Folder"/"$Subject".R.${Map}."$Mesh".label.gii -roi-right "$Folder"/"$Subject".R."$ROI"."$Mesh".shape.gii
			wb_command -set-map-names "$Folder"/"$Subject".${Map}."$Mesh".dlabel.nii -map 1 "$Subject"_${Map}
		fi
	done
done

STRINGII=""
for LowResMesh in ${LowResMeshes} ; do
	STRINGII=$(echo "${STRINGII}${AtlasSpaceFolder}/fsaverage_LR${LowResMesh}k@${AtlasSpaceFolder}/fsaverage_LR${LowResMesh}k@${LowResMesh}k_fs_LR ${T1wFolder}/fsaverage_LR${LowResMesh}k@${AtlasSpaceFolder}/fsaverage_LR${LowResMesh}k@${LowResMesh}k_fs_LR ")
done

#Add CIFTI Maps to Spec Files
for STRING in "$T1wFolder"/"$NativeFolder"@"$AtlasSpaceFolder"/"$NativeFolder"@native "$AtlasSpaceFolder"/"$NativeFolder"@"$AtlasSpaceFolder"/"$NativeFolder"@native "$AtlasSpaceFolder"@"$AtlasSpaceFolder"@"$HighResMesh"k_fs_LR ${STRINGII} ; do
	FolderI=$(echo $STRING | cut -d "@" -f 1)
	FolderII=$(echo $STRING | cut -d "@" -f 2)
	Mesh=$(echo $STRING | cut -d "@" -f 3)
	for STRINGII in sulc@dscalar thickness@dscalar curvature@dscalar aparc@dlabel aparc.a2009s@dlabel ; do #Remove BA@dlabel because it doesn't convert properly
		Map=$(echo $STRINGII | cut -d "@" -f 1)
		Ext=$(echo $STRINGII | cut -d "@" -f 2)
		if [ -e "$FolderII"/"$Subject"."$Map"."$Mesh"."$Ext".nii ] ; then
			wb_command -add-to-spec-file "$FolderI"/"$Subject"."$Mesh".wb.spec INVALID "$FolderII"/"$Subject"."$Map"."$Mesh"."$Ext".nii
		fi
	done
done

# Create midthickness Vertex Area (VA) maps
echo "Create midthickness Vertex Area (VA) maps"

for LowResMesh in ${LowResMeshes} ; do

	echo "Creating midthickness Vertex Area (VA) maps for LowResMesh: ${LowResMesh}"

	# DownSampleT1wFolder             - path to folder containing downsampled T1w files
	# midthickness_va_file            - path to non-normalized midthickness vertex area file
	# normalized_midthickness_va_file - path ot normalized midthickness vertex area file
	# surface_to_measure              - path to surface file on which to measure surface areas
	# output_metric                   - path to metric file generated by -surface-vertex-areas subcommand

	DownSampleT1wFolder=${T1wFolder}/fsaverage_LR${LowResMesh}k
	DownSampleFolder=${AtlasSpaceFolder}/fsaverage_LR${LowResMesh}k
	midthickness_va_file=${DownSampleT1wFolder}/${Subject}.midthickness_va.${LowResMesh}k_fs_LR.dscalar.nii
	normalized_midthickness_va_file=${DownSampleT1wFolder}/${Subject}.midthickness_va_norm.${LowResMesh}k_fs_LR.dscalar.nii

	for Hemisphere in L R ; do
		surface_to_measure=${DownSampleT1wFolder}/${Subject}.${Hemisphere}.midthickness.${LowResMesh}k_fs_LR.surf.gii
		output_metric=${DownSampleT1wFolder}/${Subject}.${Hemisphere}.midthickness_va.${LowResMesh}k_fs_LR.shape.gii
		wb_command -surface-vertex-areas ${surface_to_measure} ${output_metric}
	done

	# left_metric  - path to left hemisphere VA metric file
	# roi_left     - path to file of ROI vertices to use from left surface
	# right_metric - path to right hemisphere VA metric file
	# roi_right    - path to file of ROI vertices to use from right surface

	left_metric=${DownSampleT1wFolder}/${Subject}.L.midthickness_va.${LowResMesh}k_fs_LR.shape.gii
	roi_left=${DownSampleFolder}/${Subject}.L.atlasroi.${LowResMesh}k_fs_LR.shape.gii
	right_metric=${DownSampleT1wFolder}/${Subject}.R.midthickness_va.${LowResMesh}k_fs_LR.shape.gii
	roi_right=${DownSampleFolder}/${Subject}.R.atlasroi.${LowResMesh}k_fs_LR.shape.gii

	wb_command -cifti-create-dense-scalar ${midthickness_va_file} \
				-left-metric  ${left_metric} \
				-roi-left     ${roi_left} \
				-right-metric ${right_metric} \
				-roi-right    ${roi_right}

	# VAMean - mean of surface area accounted for for each vertex - used for normalization
	VAMean=$(wb_command -cifti-stats ${midthickness_va_file} -reduce MEAN)
	echo "VAMean: ${VAMean}"

	wb_command -cifti-math "VA / ${VAMean}" ${normalized_midthickness_va_file} -var VA ${midthickness_va_file}

	echo "Done creating midthickness Vertex Area (VA) maps for LowResMesh: ${LowResMesh}"

done

echo "Done creating midthickness Vertex Area (VA) maps"

echo "END"
