<template>
  <main class="page-container">
    <div class="layout-split">
      
      <!-- LEFT SIDEBAR: Header + Vertical Album List -->
      <aside class="sidebar">
        <header class="header">
          <div class="header-top">
            <div>
              <h1 class="title">Kevin Steve Sathyanath</h1>
              <p class="subtitle">Photography Index</p>
            </div>

            <!-- Upload Button & Hidden File Input -->
            <div class="upload-container">
              <input 
                type="file" 
                ref="fileInput" 
                accept="image/*" 
                style="display: none;" 
                @change="handleFileUpload" 
              />
              <button 
                class="upload-btn" 
                :disabled="isUploading" 
                @click="triggerFileChooser"
              >
                <span v-if="isUploading">Uploading...</span>
                <span v-else>+ Upload</span>
              </button>
            </div>
          </div>

          <p v-if="uploadStatus" class="upload-status">{{ uploadStatus }}</p>
        </header>

        <section class="index-section">
          <div v-if="albums.length" class="album-list">
            <button
              v-for="(album, index) in albums"
              :key="album.albumName || index"
              class="album-link"
              :class="{ active: selectedAlbum?.albumName === album.albumName }"
              @click="selectAlbum(album)"
            >
              <span class="album-title">{{ album.albumDisplayName || album.albumName }}</span>
              <span class="album-count">
                #{{ album.images ? album.images.length : 0 }}
              </span>
            </button>
          </div>

          <p v-else class="loading-state">Loading collections...</p>
        </section>
      </aside>

      <!-- RIGHT CONTENT: Selected Album Photos -->
      <section class="main-content">
        <div v-if="selectedAlbum" class="gallery-section">
          <div class="gallery-header">
            <div>
              <h2>{{ selectedAlbum.albumDisplayName || selectedAlbum.albumName }}</h2>
              <p v-if="selectedAlbum.albumDescription" class="album-description">
                {{ selectedAlbum.albumDescription }}
              </p>
            </div>
            <button class="close-btn" @click="selectedAlbum = null">&times; Close</button>
          </div>

          <!-- Photos Grid -->
          <div v-if="selectedAlbum.images && selectedAlbum.images.length" class="photo-grid">
            <div 
              v-for="(photo, pIndex) in selectedAlbum.images" 
              :key="photo.file_name || pIndex"
              class="photo-card"
            >
              <img 
                :src="photo.fileUrl || photo.thumbnailUrl" 
                :alt="photo.title || 'Photograph'" 
                loading="lazy" 
              />
              <div class="photo-meta" v-if="photo.cameraDetails">
                <span class="meta-item">{{ photo.cameraDetails.camera }}</span>
                <span class="meta-item">{{ photo.cameraDetails.lens }}</span>
                <span class="meta-item">{{ photo.cameraDetails.focalLength }} · {{ photo.cameraDetails.aperture }} · {{ photo.cameraDetails.exposure }} · ISO {{ photo.cameraDetails.iso }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-album">No images available in this collection.</p>
        </div>

        <!-- Placeholder view before an album is selected -->
        <div v-else class="select-prompt">
          <p>Select a collection from the index to view photographs.</p>
        </div>
      </section>

    </div>
  </main>
</template>

<script setup lang="ts">
import '../assets/style.css'
import axios from 'axios';
import { ref, onMounted } from 'vue';

interface CameraDetails {
  aperture: string;
  camera: string;
  exposure: string;
  focalLength: string;
  iso: string;
  lens: string;
}

interface ImageItem {
  file_name: string;
  fileUrl: string;
  thumbnailUrl: string;
  title: string;
  description: string;
  captureDate: string;
  cameraDetails?: CameraDetails;
}

interface Album {
  albumName: string;
  albumDisplayName: string;
  albumDescription?: string;
  lastUpdated?: string;
  images?: ImageItem[];
}

const albums = ref<Album[]>([]);
const selectedAlbum = ref<Album | null>(null);

// Upload state management
const fileInput = ref<HTMLInputElement | null>(null);
const isUploading = ref(false);
const uploadStatus = ref('');

const API_URL = 'https://yvd6ldf6f6.execute-api.ap-southeast-6.amazonaws.com/Prod';

onMounted(() => {
  fetchPhotos();
});

const fetchPhotos = async () => {
  try {
    const response = await axios.get(API_URL + '/albums');

    let parsedBody = response.data;
    if (response.data && typeof response.data.body === 'string') {
      parsedBody = JSON.parse(response.data.body);
    } else if (response.data && response.data.body) {
      parsedBody = response.data.body;
    }

    if (Array.isArray(parsedBody)) {
      albums.value = parsedBody;
      // Auto-select the first album with images if none is selected
      if (!selectedAlbum.value) {
        const firstWithImages = parsedBody.find(a => a.images && a.images.length);
        if (firstWithImages) {
          selectedAlbum.value = firstWithImages;
        }
      }
    } else {
      albums.value = [];
    }
  } catch (error) {
    console.error("Error fetching data: ", error);
  }
};

const selectAlbum = (album: Album) => {
  selectedAlbum.value = album;
};

// Opens native browser file chooser
const triggerFileChooser = () => {
  fileInput.value?.click();
};

// Handles file picking and triggers presigned S3 upload
const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files || !target.files.length) return;

  const file = target.files[0];
  isUploading.value = true;
  uploadStatus.value = `Requesting upload link for ${file.name}...`;

  try {
    // Step 1: POST filename to API Gateway route to obtain presigned URL
    const response = await axios.post(`${API_URL}/putImage`, {
      filename: file.name
    });

    let uploadUrl = response.data.uploadUrl;
    if (!uploadUrl && response.data.body) {
      const parsed = typeof response.data.body === 'string' ? JSON.parse(response.data.body) : response.data.body;
      uploadUrl = parsed.uploadUrl;
    }

    if (!uploadUrl) {
      throw new Error("Presigned URL was not returned by API Gateway.");
    }

    uploadStatus.value = `Uploading ${file.name} to S3...`;

    // Step 2: PUT raw image binary directly to S3 bucket
    await axios.put(uploadUrl, file, {
      headers: {
        'Content-Type': 'image/jpeg'
      }
    });

    uploadStatus.value = `Upload complete! Processing WebP pipeline...`;

    // Wait 3 seconds for background Lambda trigger to finish before refreshing list
    setTimeout(() => {
      fetchPhotos();
      uploadStatus.value = '';
    }, 3000);

  } catch (error: any) {
    console.error("Upload error:", error);
    uploadStatus.value = `Upload failed: ${error.message || 'Unknown error'}`;
  } finally {
    isUploading.value = false;
    if (target) target.value = '';
  }
};
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Corben:wght@400;700&family=Inter:wght@300;400;500&display=swap');

.page-container {
  min-height: 100vh;
  background-color: var(--background-colour, #0a0a0a);
  color: var(--headings-colour, #e5e5e5);
  font-family: 'Inter', -apple-system, sans-serif;
  padding: 3rem;
  box-sizing: border-box;
}

/* Side-by-Side Split Container */
.layout-split {
  display: flex;
  gap: 4rem;
  align-items: flex-start;
}

/* Sidebar styling (Left Column) */
.sidebar {
  width: 360px;
  flex-shrink: 0;
  position: sticky;
  top: 3rem;
  max-height: calc(100vh - 6rem);
  overflow-y: auto;
}

.header {
  margin-bottom: 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  padding-bottom: 1.25rem;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.title {
  font-family: 'Corben', serif;
  font-weight: 700;
  font-size: 1.4rem;
  margin: 0 0 0.4rem 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #888;
  margin: 0;
}

/* Upload Button */
.upload-btn {
  background: #ffffff;
  color: #0a0a0a;
  border: none;
  padding: 0.45rem 0.85rem;
  border-radius: 4px;
  font-family: 'Inter', sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.upload-btn:hover:not(:disabled) {
  background: #e0e0e0;
  transform: translateY(-1px);
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.upload-status {
  font-size: 0.75rem;
  color: #aaa;
  margin: 0.75rem 0 0 0;
  font-style: italic;
}

.album-list {
  display: flex;
  flex-direction: column;
}

.album-link {
  background: none;
  border: none;
  color: #bbb;
  text-align: left;
  font-family: inherit;
  font-size: 1rem;
  padding: 0.65rem 0;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  transition: all 0.2s ease;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
}

.album-link:hover {
  color: #ffffff;
  padding-left: 0.4rem;
  border-bottom-color: rgba(255, 255, 255, 0.5);
}

.album-link.active {
  color: #ffffff;
  font-weight: 500;
  padding-left: 0.4rem;
  border-bottom: 1px solid #ffffff;
}

.album-count {
  font-size: 0.8rem;
  color: #666;
  margin-left: 0.75rem;
  font-variant-numeric: tabular-nums;
}

/* Main Content Area (Right Column) */
.main-content {
  flex-grow: 1;
  min-width: 0;
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.gallery-header h2 {
  font-family: 'Corben', serif;
  font-size: 1.3rem;
  margin: 0 0 0.4rem 0;
}

.album-description {
  color: #999;
  font-size: 0.9rem;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
  padding: 0.3rem 0.7rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #222;
  color: #fff;
  border-color: #666;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2rem;
}

.photo-card {
  display: flex;
  flex-direction: column;
}

.photo-card img {
  width: 100%;
  height: auto;
  object-fit: cover;
  border-radius: 2px;
  display: block;
}

.photo-meta {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.75rem;
  color: #777;
}

.select-prompt, .loading-state, .empty-album {
  color: #666;
  font-style: italic;
  padding-top: 1rem;
}

@media (max-width: 900px) {
  .layout-split {
    flex-direction: column;
    gap: 2rem;
  }

  .sidebar {
    width: 100%;
    position: relative;
    top: 0;
    max-height: none;
  }
}
</style>