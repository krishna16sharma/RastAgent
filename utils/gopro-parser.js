const gpmfExtract = require('gpmf-extract');
const goproTelemetry = require('gopro-telemetry');
const fs = require('fs');
const path = require('path');

const CHUNK_SIZE = 512 * 1024 * 1024; // 512MB

/**
 * Read a file into a Buffer, handling files > 2GB by reading in chunks.
 */
function readLargeFile(filePath) {
  const stat = fs.statSync(filePath);
  if (stat.size <= CHUNK_SIZE) {
    return fs.readFileSync(filePath);
  }
  const chunks = [];
  const fd = fs.openSync(filePath, 'r');
  let bytesRead = 0;
  while (bytesRead < stat.size) {
    const size = Math.min(CHUNK_SIZE, stat.size - bytesRead);
    const buf = Buffer.alloc(size);
    fs.readSync(fd, buf, 0, size, bytesRead);
    chunks.push(buf);
    bytesRead += size;
  }
  fs.closeSync(fd);
  return Buffer.concat(chunks);
}

/**
 * Extract raw GPMF data from a GoPro MP4 buffer.
 */
async function extractGPMF(buffer) {
  return gpmfExtract(buffer);
}

/**
 * Parse telemetry from raw GPMF data.
 * @param {object} raw - Output from gpmfExtract
 * @param {string[]} [streams] - Stream names to extract (e.g. ['GPS5', 'ACCL']). Null for all.
 * @returns {object} Parsed telemetry object
 */
async function parseTelemetry(raw, streams = null) {
  const opts = streams ? { stream: streams } : {};
  return goproTelemetry(raw, opts);
}

/**
 * Get GPS samples from telemetry, optionally filtering for locked signals.
 * @param {object} telemetry - Output from parseTelemetry
 * @param {object} [options]
 * @param {boolean} [options.lockedOnly=false] - Only return samples with GPS fix
 * @param {number} [options.minFix=2] - Minimum fix value (2=2D, 3=3D)
 * @returns {Array<{lat, lon, alt, speed2d, speed3d, date, cts, fix, precision}>}
 */
function getGPSSamples(telemetry, { lockedOnly = false, minFix = 2 } = {}) {
  const device = telemetry['1'];
  if (!device?.streams?.GPS5) return [];

  const samples = device.streams.GPS5.samples;
  const mapped = samples.map(s => ({
    lat: s.value[0],
    lon: s.value[1],
    alt: s.value[2],
    speed2d: s.value[3],
    speed3d: s.value[4],
    date: s.date,
    cts: s.cts,
    fix: s.sticky?.fix ?? 0,
    precision: s.sticky?.precision ?? 9999,
  }));

  if (lockedOnly) {
    return mapped.filter(s => s.fix >= minFix);
  }
  return mapped;
}

/**
 * List available telemetry stream names from parsed telemetry.
 */
function listStreams(telemetry) {
  const device = telemetry['1'];
  if (!device?.streams) return [];
  return Object.keys(device.streams);
}

/**
 * Parse a single GoPro MP4 file end-to-end.
 * @param {string} filePath - Path to the MP4 file
 * @param {object} [options]
 * @param {string[]} [options.streams] - Streams to extract (null for all)
 * @param {boolean} [options.lockedOnly] - Filter GPS to locked samples only
 * @param {number} [options.minFix] - Minimum GPS fix value
 * @returns {Promise<{telemetry, gps, availableStreams}>}
 */
async function parseFile(filePath, { streams = null, lockedOnly = false, minFix = 2 } = {}) {
  const buffer = readLargeFile(filePath);
  const raw = await extractGPMF(buffer);
  const telemetry = await parseTelemetry(raw, streams);
  const gps = getGPSSamples(telemetry, { lockedOnly, minFix });
  const availableStreams = listStreams(telemetry);
  return { telemetry, gps, availableStreams };
}

/**
 * Parse all MP4 files in a directory.
 * @param {string} dirPath - Directory containing MP4 files
 * @param {object} [options] - Same options as parseFile
 * @returns {Promise<Object<string, {telemetry, gps, availableStreams}>>} Keyed by filename
 */
async function parseDirectory(dirPath, options = {}) {
  const files = fs.readdirSync(dirPath)
    .filter(f => f.toLowerCase().endsWith('.mp4'))
    .sort();

  const results = {};
  for (const file of files) {
    const filePath = path.join(dirPath, file);
    console.log(`Parsing ${file}...`);
    results[file] = await parseFile(filePath, options);
    console.log(`  ${results[file].gps.length} GPS samples, streams: [${results[file].availableStreams.join(', ')}]`);
  }
  return results;
}

/**
 * Chunk a GoPro MP4 into smaller segments preserving telemetry.
 * Requires ffmpeg on PATH.
 * @param {string} inputPath - Path to source MP4
 * @param {string} outputDir - Directory for chunks
 * @param {number} [duration=120] - Chunk duration in seconds
 * @returns {string[]} Array of chunk file paths
 */
function chunkVideo(inputPath, outputDir, duration = 120) {
  const { execSync } = require('child_process');

  fs.mkdirSync(outputDir, { recursive: true });

  const probe = execSync(
    `ffprobe -v error -show_entries format=duration -of csv=p=0 "${inputPath}"`,
    { encoding: 'utf8' }
  );
  const total = Math.floor(parseFloat(probe.trim()));
  const basename = path.basename(inputPath, path.extname(inputPath));

  const chunks = [];
  let i = 0;
  let start = 0;
  while (start < total) {
    const outFile = path.join(outputDir, `${basename}_chunk_${String(i).padStart(3, '0')}.mp4`);
    execSync(
      `ffmpeg -y -ss ${start} -i "${inputPath}" -map 0:v -map 0:a -map 0:3 -c copy -t ${duration} -f mp4 "${outFile}"`,
      { stdio: 'pipe' }
    );
    chunks.push(outFile);
    i++;
    start += duration;
  }
  return chunks;
}

module.exports = {
  readLargeFile,
  extractGPMF,
  parseTelemetry,
  getGPSSamples,
  listStreams,
  parseFile,
  parseDirectory,
  chunkVideo,
};
