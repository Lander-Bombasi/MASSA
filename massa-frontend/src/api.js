// src/api.js
import axios from "axios";

const API_BASE = "http://192.168.100.18:5000"; // Update if Flask IP changes

export const getWeight = () =>
  axios.get(`${API_BASE}/weight`).then(res => res.data);

export const detectBanana = () =>
  axios.get(`${API_BASE}/detect`).then(res => res.data);

export const recordItem = (item) =>
  axios.post(`${API_BASE}/record`, item).then(res => res.data);

export const toggleTransaction = () =>
  axios.post(`${API_BASE}/transaction`).then(res => res.data);
