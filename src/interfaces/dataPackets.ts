export interface ExifData {
  width?: number;
  height?: number;
  aperture?: number;
  exposure?: number;
  ISO?: number;
  focalLength?: number; // camelCase is more standard in TS
  lensModel?: string;
}

export interface PhotoEntry {
  uId: string;
  fileName: string;
  originalURL: string;
  thumbnailURL: string;
  description?: string;
  exifData: ExifData;
}

// This represents the "Daily Album Record" we discussed earlier
export interface AlbumRecord {
  pk: string; 
  sk: string; 
  photos: PhotoEntry[];
  entityType: "ALBUM_BATCH";
}