# zillow-map

Simple Vue app for displaying JSON data created via https://github.com/vforvasquez/zillow-extension browser extension.

## Project Setup

```sh
npm install
```

### Load House Data

Copy/paste your House JSON data into `public/data/houses.json`

### Load Env Vars

- Create .env file
- Save Google API key to env var `VITE_GOOGLE_API_KEY`, e.g. `VITE_GOOGLE_API_KEY=123..`. NOTE: Originally I was using Google to geoencode street addresses into lat/long values. I eventually found a way to get this data from Zillow directly but prefer using Google Maps opposed to open source map apis and the cost is essentially zero.

### Compile and Hot-Reload for Development

Since I'm only running this locally I am not spending time on optimizing builds and using dev mode.

```sh
npm run dev
```

### TODO

- Filtering
- Search
- Custom Tags
- Collections
