import React, { useState, useEffect, useReducer, useCallback } from "react";
import Numpad from "../components/Numpad";
import "./ScalePage.css";

const API = "http://192.168.93.11:5000";

const initialState = {
  weight: 0,
  pricePerKg: "",
  amount: 0,
  payment: "",
  change: 0,
  total: 0,
  records: [],
  bananaType: "",
  isLoading: false,
  error: null,
  connectionStatus: "disconnected",
  isManualPrice: false,
  isPaymentMode: false
};

const reducer = (state, action) => {
  switch (action.type) {
    case 'SET_WEIGHT':
      return { 
        ...state, 
        weight: action.payload,
        amount: state.pricePerKg ? parseFloat((action.payload * state.pricePerKg).toFixed(2)) : state.amount
      };
    case 'SET_PRICE':
      return { ...state, pricePerKg: action.payload };
    case 'SET_AMOUNT':
      return { ...state, amount: action.payload };
    case 'SET_PAYMENT':
      return { 
        ...state, 
        payment: action.payload,
        change: parseFloat((parseFloat(action.payload || 0) - state.total).toFixed(2))
      };
    case 'SET_CHANGE':
      return { ...state, change: action.payload };
    case 'SET_TOTAL':
      return { ...state, total: parseFloat(action.payload.toFixed(2)) };
    case 'SET_BANANA_TYPE':
      return { 
        ...state, 
        bananaType: action.payload.type,
        pricePerKg: action.payload.price,
        amount: parseFloat((state.weight * action.payload.price).toFixed(2)),
        isManualPrice: false
      };
    case 'SET_MANUAL_PRICE':
      return { 
        ...state, 
        pricePerKg: action.payload,
        amount: parseFloat((state.weight * action.payload).toFixed(2)),
        isManualPrice: true
      };
    case 'RECORD_ITEM':
      const newItem = {
        bananaType: state.bananaType || "Manual",
        weight: parseFloat(state.weight.toFixed(3)),
        pricePerKg: state.pricePerKg || 0,
        amount: parseFloat((state.weight * (state.pricePerKg || 0)).toFixed(2))
      };
      return {
        ...state,
        records: [...state.records, newItem],
        total: parseFloat((state.total + parseFloat(newItem.amount)).toFixed(2)),
        bananaType: "",
        pricePerKg: "",
        amount: 0,
        weight: 0,
        isManualPrice: false
      };
    case 'COMPLETE_TRANSACTION':
      return {
        ...state,
        records: [],
        total: 0,
        payment: "",
        change: 0,
        isPaymentMode: false
      };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_STATUS':
      return { ...state, connectionStatus: action.payload };
    case 'APPEND_INPUT':
      if (state.isPaymentMode) {
        const newPayment = state.payment + action.payload;
        return {
          ...state,
          payment: newPayment,
          change: parseFloat((parseFloat(newPayment || 0) - state.total).toFixed(2))
        };
      } else {
        const newPrice = state.pricePerKg + action.payload;
        return {
          ...state,
          pricePerKg: newPrice,
          amount: parseFloat((state.weight * newPrice).toFixed(2))
        };
      }
    case 'CLEAR_INPUT':
      if (state.isPaymentMode) {
        return { ...state, payment: "", change: 0 };
      } else {
        return { ...state, pricePerKg: "", amount: 0 };
      }
    case 'SET_PAYMENT_MODE':
      return { ...state, isPaymentMode: action.payload };
    default:
      return state;
  }
};

const ScalePage = () => {
  const [state, dispatch] = useReducer(reducer, initialState);

  const fetchWeight = useCallback(async () => {
    try {
      const response = await fetch(`${API}/weight`);
      if (!response.ok) throw new Error(await response.text() || 'Weight fetch failed');

      const data = await response.json();
      if (data.status === 'success') {
        const rawWeight = parseFloat(data.weight);
        
        // Only update if the change is significant (>10g) to prevent flickering
        if (Math.abs(rawWeight - state.weight) > 0.01 || rawWeight === 0) {
          dispatch({ type: 'SET_WEIGHT', payload: rawWeight });
        }

        dispatch({ type: 'SET_STATUS', payload: data.connected ? 'connected' : 'disconnected' });
      } else {
        dispatch({ type: 'SET_STATUS', payload: 'disconnected' });
      }
    } catch (error) {
      console.error("Weight polling error:", error);
      dispatch({ type: 'SET_STATUS', payload: 'disconnected' });
    }
  }, [state.weight]);

  useEffect(() => {
    const weightPolling = setInterval(fetchWeight, 500);
    return () => clearInterval(weightPolling);
  }, [fetchWeight]);

  const handleNumberClick = (value) => dispatch({ type: 'APPEND_INPUT', payload: value });
  const handleClear = () => dispatch({ type: 'CLEAR_INPUT' });
  const dismissError = () => dispatch({ type: 'SET_ERROR', payload: null });

  const handleDetect = async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await fetch(`${API}/detect`);
      if (!response.ok) throw new Error(await response.text() || 'Detection failed');
      const data = await response.json();

      if (data.status === 'success') {
        dispatch({ 
          type: 'SET_BANANA_TYPE', 
          payload: { type: data.banana_type, price: data.price_per_kg } 
        });
      } else {
        dispatch({ type: 'SET_ERROR', payload: data.error || 'Detection failed' });
      }
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleRecord = () => {
    if (state.weight > 0) {
      dispatch({ type: 'RECORD_ITEM' });
    } else {
      dispatch({ type: 'SET_ERROR', payload: "Cannot record zero weight" });
    }
  };

  const handleTare = async () => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await fetch(`${API}/tare`, { method: 'POST' });
      if (!response.ok) throw new Error(await response.text() || 'Tare failed');
      const data = await response.json();
      if (data.status !== 'success') {
        dispatch({ type: 'SET_ERROR', payload: data.error || 'Tare failed' });
      }
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleTransaction = async () => {
    if (state.isPaymentMode) {
      if (state.records.length === 0) return dispatch({ type: 'SET_ERROR', payload: "No items to complete transaction" });
      if (parseFloat(state.payment) < state.total) return dispatch({ type: 'SET_ERROR', payload: "Payment amount is insufficient" });

      dispatch({ type: 'SET_LOADING', payload: true });
      try {
        const response = await fetch(`${API}/transaction`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            payment: parseFloat(state.payment), 
            items: state.records.map(item => ({ ...item, amount: parseFloat(item.amount) }))
          })
        });
        if (!response.ok) throw new Error(await response.text() || 'Transaction failed');

        const data = await response.json();
        if (data.status === 'success') {
          dispatch({ type: 'COMPLETE_TRANSACTION' });
        } else {
          dispatch({ type: 'SET_ERROR', payload: data.error || 'Transaction failed' });
        }
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error.message });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    } else {
      if (state.records.length === 0) return dispatch({ type: 'SET_ERROR', payload: "No items recorded" });
      dispatch({ type: 'SET_PAYMENT_MODE', payload: true });
    }
  };

  return (
    <div className="scale-container">
      <div className="display-panel">
        <div className="weight-display">
          <h1>{state.weight.toFixed(3)} kg</h1>
          <div className={`status ${state.connectionStatus}`}>
            {state.connectionStatus.toUpperCase()}
          </div>
        </div>

        <div className="product-info">
          <div className="info-row"><span>Type:</span><span>{state.bananaType || '-'}</span></div>
          <div className="info-row"><span>Price/kg:</span><span>{state.pricePerKg ? `₱${state.pricePerKg}` : '-'}</span></div>
          <div className="info-row"><span>Amount:</span><span>{state.amount ? `₱${parseFloat(state.amount).toFixed(2)}` : '-'}</span></div>
        </div>

        <div className="transaction-section">
          <h3>Transaction</h3>
          <div className="items-list">
            <ul>
              {state.records.map((item, index) => (
                <li key={index}>
                  {item.bananaType}: {parseFloat(item.weight).toFixed(3)}kg × ₱{item.pricePerKg} = ₱{parseFloat(item.amount).toFixed(2)}
                </li>
              ))}
            </ul>
          </div>
          <div className="totals">
            <div className="total-row">
              <span>Total:</span>
              <span>₱{state.total.toFixed(2)}</span>
            </div>
            {state.isPaymentMode && (
              <>
                <div className="info-row"><span>Payment:</span><span>₱{state.payment || '0.00'}</span></div>
                <div className="info-row"><span>Change:</span><span>₱{state.change.toFixed(2)}</span></div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="input-panel">
        <Numpad
          onClick={handleNumberClick}
          onClear={handleClear}
          onDetect={handleDetect}
          onRecord={handleRecord}
          onTransaction={handleTransaction}
          onTare={handleTare}
          disabled={state.isLoading}
          mode={state.isPaymentMode ? 'payment' : 'price'}
        />
      </div>
    </div>
  );
};

export default ScalePage;