#!/usr/bin/env bash
# 12주차 방식: edit.json 계획대로 ffmpeg 렌더 → ffprobe 검수
# 사전 준비: python video/slides.py && python video/rec.py 로 video/build/ 에 장면 생성
set -e
cd "$(dirname "$0")/.."
B=video/build
mkdir -p media && cp $B/thumbnail.png media/thumbnail.png
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.25*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.2*t))+0.18*sin(2*PI*277.18*t)*(0.6+0.4*sin(2*PI*0.15*t+1))+0.15*sin(2*PI*329.63*t)*(0.6+0.4*sin(2*PI*0.1*t+2))':s=44100:d=90" \
  -af "lowpass=f=1500,afade=t=in:d=1.5,afade=t=out:st=88.5:d=1.5,volume=0.5" $B/bgm.wav
V="fps=24,scale=1920:1080,setsar=1,format=yuv420p"
ffmpeg -v error -y \
 -loop 1 -t 3 -i $B/thumbnail.png -loop 1 -t 6 -i $B/arch.png \
 -ss 0.3 -t 11 -i $B/term.webm -ss 0.3 -t 31 -i $B/viewer.webm \
 -loop 1 -t 6 -i $B/plan.png -loop 1 -t 6 -i $B/arch2.png \
 -ss 0.3 -t 22 -i $B/reply.webm -loop 1 -t 5 -i $B/outro.png \
 -i $B/bgm.wav -i media/thumbnail.png \
 -filter_complex "\
[0:v]$V,fade=t=out:st=2.7:d=0.3[v0];\
[1:v]$V,fade=t=in:d=0.3,fade=t=out:st=5.7:d=0.3[v1];\
[2:v]$V,fade=t=in:d=0.3[v2];\
[3:v]$V,fade=t=in:d=0.3,fade=t=out:st=30.7:d=0.3[v3];\
[4:v]$V,fade=t=in:d=0.3,fade=t=out:st=5.7:d=0.3[v4];\
[5:v]$V,fade=t=in:d=0.3,fade=t=out:st=5.7:d=0.3[v5];\
[6:v]$V,fade=t=in:d=0.3,fade=t=out:st=21.7:d=0.3[v6];\
[7:v]$V,fade=t=in:d=0.3[v7];\
[v0][v1][v2][v3][v4][v5][v6][v7]concat=n=8:v=1:a=0,subtitles=video/subs.srt:force_style='FontName=Noto Sans CJK KR,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=28,Bold=1'[v];\
[8:a]volume=0.25,atrim=0:90[a]" \
 -map "[v]" -map "[a]" -map 9 -c:v:0 libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -r 24 \
 -c:v:1 png -disposition:v:1 attached_pic -c:a aac -b:a 128k -movflags +faststart media/demo.mp4
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact media/demo.mp4
