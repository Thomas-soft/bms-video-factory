import {renderVideo} from '@revideo/renderer';

const t0 = Date.now();
const out = await renderVideo({
  projectFile: './src/project.tsx',
  settings: {
    outFile: 'out.mp4',
    logProgress: true,
    workers: 1,                       // 2 workers saturent 16 Go
    dimensions: [1920, 1080],
    fps: 30,
    ffmpeg: {ffmpegLogLevel: 'error'},
  },
});
console.log(`RENDU ${out} en ${((Date.now() - t0) / 1000).toFixed(1)} s`);
