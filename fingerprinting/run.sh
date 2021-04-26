#docker run -dit --volume="/home/richard/data:/data" -u $(id -u):$(id -g) --name=rb-mlsdr mlsdr:latest		#can't use this if you want to do anything inside as root
#docker run -dit --volume="/home/richard/ML-SDR/data:/data" --name=rb-mlsdr mlsdr:latest
docker run -dit --runtime=nvidia --volume="/home/richard/siamese/data:/data" --name=rb-mlsdr-siamese rb-mlsdr-siamese:latest
