const serverless = require('serverless-http');
const path = require('path');
// ensure environment variables are loaded
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
// import the Express app (server.js exports the app)
const app = require('../server');
module.exports = serverless(app);