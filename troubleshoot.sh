#!/bin/bash

# ML Gateway Troubleshooting Script

echo "🔍 ML Gateway Troubleshooting"
echo "============================"

# Check services status
echo "📊 Service Status:"
echo "OpenSearch:"
sudo systemctl status opensearch --no-pager -l | head -10
echo ""
echo "ML Gateway:"
sudo systemctl status ml-gateway --no-pager -l | head -10
echo ""

# Check ports
echo "🔌 Port Status:"
netstat -tlnp | grep -E ':(8000|9200)' || echo "No services listening on 8000/9200"
echo ""

# Check OpenSearch health
echo "🏥 OpenSearch Health:"
curl -s http://localhost:9200/_cluster/health | python3 -c "import sys, json; data=json.load(sys.stdin); print('Status:', data.get('status', 'unknown')); print('Nodes:', data.get('number_of_nodes', 0))" 2>/dev/null || echo "OpenSearch not responding"
echo ""

# Check Gateway health
echo "🌐 Gateway Health:"
curl -s http://localhost:8000/health | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data, indent=2))" 2>/dev/null || echo "Gateway not responding"
echo ""

# Check logs
echo "📋 Recent Logs:"
echo "OpenSearch errors:"
sudo journalctl -u opensearch -n 5 --no-pager 2>/dev/null | grep -i error | tail -3 || echo "No recent errors"
echo ""
echo "Gateway errors:"
sudo journalctl -u ml-gateway -n 5 --no-pager 2>/dev/null | grep -i error | tail -3 || echo "No recent errors"
echo ""

# Check file permissions
echo "🔐 File Permissions:"
ls -la /opt/ml-gateway/ | head -5
echo ""

# Test manual gateway start
echo "🧪 Testing manual gateway start..."
sudo -u gateway bash -c "cd /opt/ml-gateway && source venv/bin/activate && timeout 5 python3 -c 'import main; print(\"Import successful\")'" 2>&1 | head -5 || echo "Import failed"
echo ""

echo "💡 Common Fixes:"
echo "1. Restart services: sudo systemctl restart opensearch && sudo systemctl restart ml-gateway"
echo "2. Check logs: sudo journalctl -u ml-gateway -f"
echo "3. Test manually: sudo -u gateway bash -c 'cd /opt/ml-gateway && source venv/bin/activate && python3 main.py'"
echo "4. Check ports: sudo netstat -tlnp | grep 8000"