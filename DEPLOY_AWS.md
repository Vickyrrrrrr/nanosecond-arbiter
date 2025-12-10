# ☁️ Deploying to AWS

Follow these steps to run your bot 24/7 on the cloud.

## 1. Launch a Server (EC2)
1.  Log in to [AWS Console](https://console.aws.amazon.com/ec2).
2.  Click **Launch Instance**.
3.  **Name**: `NanosecondArbiter`
4.  **OS Image**: `Ubuntu Server 24.04 LTS` (or 22.04).
5.  **Instance Type**: `t2.micro` or `t3.micro` (Free Tier eligible).
6.  **Key Pair**: Create a new key pair (e.g., `arbiter-key.pem`) and download it.
7.  **Network Settings**: Allows SSH traffic from Anywhere.
    *   **IMPORTANT**: Add a Custom TCP Rule to allow Port `8083` (for Dashboard).

## 2. Upload Your Code
Open your local terminal (where this folder is) and run:

```bash
# Fix key permissions first
chmod 400 path/to/arbiter-key.pem

# Upload folder (replace IP and Key Path)
scp -i path/to/arbiter-key.pem -r . ubuntu@<YOUR_AWS_IP>:/home/ubuntu/nanosecond-arbiter
```

## 3. Run Setup Script
SSH into your server:
```bash
ssh -i path/to/arbiter-key.pem ubuntu@<YOUR_AWS_IP>
```

Then inside the server run:
```bash
cd nanosecond-arbiter
chmod +x deploy/setup.sh
./deploy/setup.sh
```

## 4. Configure & Start
The setup script will ask you to edit the service file to add your API keys:

```bash
sudo nano /etc/systemd/system/nanosecond-trader.service
```
*   Replace `YOUR_BINANCE_API_KEY_HERE` with your real keys.
*   Press `Ctrl+O` (Save), `Enter`, then `Ctrl+X` (Exit).

Finally, start the bots:
```bash
sudo systemctl daemon-reload
sudo systemctl start nanosecond-dashboard
sudo systemctl start nanosecond-trader
```

## 5. Verify
Open your browser to:
`http://<YOUR_AWS_IP>:8083`

Your bot is now running 24/7! 🚀
