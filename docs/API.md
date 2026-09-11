# Dispute Webhook API

This API is designed to receive real-time webhook events from payment processors (e.g., Stripe, PayPal) whenever a dispute is raised against an order. 

The endpoint utilizes **Confidence Engine (CE) 3.0** matching logic to cross-reference historical data and automatically block users if the fraud confidence score exceeds the automated threshold.

---

## Endpoint Details

**URL:** `/api/v1/dispute-webhook`  
**Method:** `POST`  
**Content-Type:** `application/json`

### Request Payload

| Field            | Type   | Description                                                                 |
|------------------|--------|-----------------------------------------------------------------------------|
| `dispute_id`     | String | Unique identifier from the payment processor.                               |
| `order_id`       | String | Internal order identifier.                                                  |
| `user_id`        | String | Internal user identifier.                                                   |
| `reason`         | String | The processor's classification of the dispute (e.g., `empty_box`, `wrong_item`, `item_defective`). |
| `evidence_score` | Float  | Initial evidence rating from the processor (0.0 to 1.0).                    |

### Example Request

```json
{
  "dispute_id": "dp_1234abcd5678",
  "order_id": "ORD-12345",
  "user_id": "usr_789",
  "reason": "empty_box",
  "evidence_score": 0.85
}
```

---

## Response 

The response includes the actions taken by the backend system based on the CE 3.0 analysis.

### Example Response

```json
{
  "status": "received",
  "dispute_id": "dp_1234abcd5678",
  "action_taken": "user_blocked",
  "ce_analysis": {
    "confidence_score": 100.0,
    "auto_block": true,
    "ce_version": "3.0"
  }
}
```

### Action Taken Values
- `user_blocked`: The confidence score exceeded 85%, and the user account has been automatically disabled.
- `flagged_for_review`: The confidence score is below 85% or the dispute reason requires manual intervention. The case has been routed to the support team queue.
