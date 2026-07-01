import { StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";

export default function DebugImage({ label, uri }) {
  if (!uri) return null;

  return (
    <View style={styles.cropItem}>
      <Text style={styles.cropLabel}>{label}</Text>
      <Image source={{ uri }} style={styles.cropImage} contentFit="contain" />
    </View>
  );
}

const styles = StyleSheet.create({
  cropItem: {
    gap: 6,
  },
  cropLabel: {
    color: "#c6d3df",
    fontSize: 13,
    fontWeight: "700",
  },
  cropImage: {
    width: "100%",
    height: 120,
    borderRadius: 8,
    backgroundColor: "#07090c",
  },
});
