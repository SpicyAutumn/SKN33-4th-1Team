import photos from './heritagePhotos.json';

// Today's recommendations use only the team's collected encyclopedia media.
export default photos.filter((photo) => {
  try {
    return /^E\d+$/.test(photo.eid || '') && /^KOGL[1-4]$/.test(photo.kogl_type || '')
      && new URL(photo.source_page).hostname === 'encykorea.aks.ac.kr';
  } catch { return false; }
});
