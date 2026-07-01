import { Alert, FlatList, SafeAreaView, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

import CardGridItem from "../components/CardGridItem";

export default function BinderScreen({ cards, onSelectCard, onRemoveCard }) {
  const confirmRemove = (card) => {
    Alert.alert(
      "바인더에서 삭제",
      `${card.name || "이 카드"}를 바인더에서 삭제할까요?`,
      [
        { text: "취소", style: "cancel" },
        { text: "삭제", style: "destructive", onPress: () => onRemoveCard?.(card.card_id) },
      ],
    );
  };

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>바인더</Text>
        <Text style={styles.body}>
          {cards.length > 0
            ? `${cards.length}장의 카드를 담았습니다. 길게 눌러 삭제할 수 있어요.`
            : "카드 상세 화면에서 바인더에 추가한 카드가 여기에 표시됩니다."}
        </Text>
      </View>

      <FlatList
        data={cards}
        keyExtractor={(item) => item.card_id}
        numColumns={2}
        columnWrapperStyle={styles.gridRow}
        contentContainerStyle={styles.gridContent}
        renderItem={({ item }) => (
          <CardGridItem card={item} onPress={onSelectCard} onLongPress={confirmRemove} />
        )}
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Ionicons name="albums-outline" size={32} color="#5b6673" />
            <Text style={styles.emptyText}>아직 바인더에 담은 카드가 없습니다.</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#101418",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
  },
  title: {
    color: "#f8fbff",
    fontSize: 24,
    fontWeight: "700",
  },
  body: {
    color: "#c6d3df",
    fontSize: 14,
    marginTop: 4,
    lineHeight: 20,
  },
  gridContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
    flexGrow: 1,
  },
  gridRow: {
    justifyContent: "space-between",
    marginBottom: 12,
  },
  emptyBox: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingTop: 60,
    gap: 8,
  },
  emptyText: {
    color: "#5b6673",
    fontSize: 14,
    textAlign: "center",
  },
});
