import { Pressable, StyleSheet, Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@expo/vector-icons";

export default function CardGridItem({ card, onPress, onLongPress }) {
  return (
    <Pressable
      style={styles.tile}
      onPress={() => onPress?.(card)}
      onLongPress={onLongPress ? () => onLongPress(card) : undefined}
    >
      <View style={styles.imageWrap}>
        {card.image_url ? (
          <Image source={{ uri: card.image_url }} style={styles.image} contentFit="cover" />
        ) : (
          <View style={[styles.image, styles.imagePlaceholder]}>
            <Ionicons name="image-outline" size={22} color="#7c8896" />
          </View>
        )}
      </View>

      <Text style={styles.name} numberOfLines={1}>
        {card.name || "이름 미확인"}
      </Text>
      <Text style={styles.meta} numberOfLines={1}>
        {card.card_number || "-"}
      </Text>
      <Text style={styles.meta} numberOfLines={1}>
        {card.set_code || "-"} · {card.rarity || "-"}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    width: "47%",
    backgroundColor: "#161d24",
    borderRadius: 10,
    padding: 8,
    gap: 4,
  },
  imageWrap: {
    width: "100%",
    aspectRatio: 6.3 / 8.8,
    borderRadius: 6,
    overflow: "hidden",
    backgroundColor: "#07090c",
    marginBottom: 6,
  },
  image: {
    width: "100%",
    height: "100%",
  },
  imagePlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  name: {
    color: "#f8fbff",
    fontSize: 14,
    fontWeight: "800",
  },
  meta: {
    color: "#c6d3df",
    fontSize: 12,
  },
});
