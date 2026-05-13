import rwaRWS as rwaRWS
import io

#rws = rwaRWS.load_2057("Levels/banquet/8_WavDictXBOX.rws")
rws1 = rwaRWS.load_2057("Levels/banquet/1733_LANG_German.rws")

newsub = rwaRWS.import_wav("meme.wav", name="cherryspidersaycherry_MEME")
#rws1.file_data.subsongs.append(newsub)

buf = io.BytesIO()
sub = rws1.getSubstream(28)
sub.write(buf, 469893156)
with open("before", "wb") as f:
    f.write(buf.getvalue())

#rws1.replace_subsong(28, newsub)
subwavdata, _, _, _ = rwaRWS._import_wav_getData("videoplayback-[AudioTrimmer.com].wav")
rws1.file_data.subsongs[28].stream_data.data = subwavdata

buf2 = io.BytesIO()
sub2 = rws1.getSubstream(28)
sub2.write(buf2, 469893156)
with open("after", "wb") as f:
    f.write(buf2.getvalue())
    
rws1.save("1733_LANG_German.rws")

rws = rwaRWS.load_2057("1733_LANG_German.rws")
rws.present_streams()

#sub.export_wav(f"{sub.header_info.stream_name}.wav")