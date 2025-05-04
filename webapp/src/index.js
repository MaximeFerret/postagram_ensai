import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import axios from 'axios'
// Importing the Bootstrap CSS
import 'bootstrap/dist/css/bootstrap.min.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
axios.defaults.baseURL = "http://tf-lb-20250504133335453800000003-1481159754.us-east-1.elb.amazonaws.com"  
// ^^^^
// EC2 > Equilibrage de charge > http://<copier le nom du DNS le Load Balancer créé>

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
