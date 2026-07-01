import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { fetchCardCandidates } from "../api/cards";
import CardGridItem from "../components/CardGridItem";

export default function SearchScreen({ onSelectCard }) {
  const [name, setName] = useState("");
  const [number, setNumber] = useState("");
  const [setCode, setSetCode] = useState("");
  const [rarity, setRarity] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [results, setResults] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  const runSearch = async () => {
    if (!name.trim() && !number.trim() && !setCode.trim() && !rarity.trim()) {
      Alert.alert("검색 조건 필요", "카드명, 번호, 세트, 레어도 중 하나 이상 입력해주세요.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");

    try {
      const candidates = await fetchCardCandidates({ name, number, setCode, rarity });
      setResults(candidates);
      setHasSearched(true);
    } catch (error) {
      setErrorMessage("카드 조회 중 문제가 발생했습니다. 서버 연결을 확인해주세요.");
      setResults([]);
      setHasSearched(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>카드 찾기</Text>
        <Text style={styles.body}>이름, 번호, 세트, 레어도로 카드를 조회합니다.</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="카드명 (예: 리자몽 ex)"
          placeholderTextColor="#5b6673"
          value={name}
          onChangeText={setName}
          returnKeyType="search"
          onSubmitEditing={runSearch}
        />
        <View style={styles.row}>
          <TextInput
            style={[styles.input, styles.inputHalf]}
            placeholder="카드 번호 (예: 022)"
            placeholderTextColor="#5b6673"
            value={number}
            onChangeText={setNumber}
          />
          <TextInput
            style={[styles.input, styles.inputHalf]}
            placeholder="레어도 (예: RR)"
            placeholderTextColor="#5b6673"
            value={rarity}
            onChangeText={setRarity}
            autoCapitalize="characters"
          />
        </View>
        <TextInput
          style={styles.input}
          placeholder="세트 코드 (예: M4)"
          placeholderTextColor="#5b6673"
          value={setCode}
          onChangeText={setCode}
          autoCapitalize="characters"
        />

        <Pressable style={styles.searchButton} onPress={runSearch} disabled={isLoading}>
          {isLoading ? (
            <ActivityIndicator color="#101418" />
          ) : (
            <>
              <Ionicons name="search" size={18} color="#101418" />
              <Text style={styles.searchButtonText}>검색</Text>
            </>
          )}
        </Pressable>
      </View>

      {errorMessage ? (
        <View style={styles.messageBox}>
          <Text style={styles.messageText}>{errorMessage}</Text>
        </View>
      ) : null}

      <FlatList
        data={results}
        keyExtractor={(item) => item.card_id}
        numColumns={2}
        columnWrapperStyle={styles.gridRow}
        contentContainerStyle={styles.gridContent}
        renderItem={({ item }) => <CardGridItem card={item} onPress={onSelectCard} />}
        ListEmptyComponent={
          !isLoading && hasSearched && !errorMessage ? (
            <View style={styles.emptyBox}>
              <Ionicons name="file-tray-outline" size={28} color="#5b6673" />
              <Text style={styles.emptyText}>조건에 맞는 카드가 없습니다.</Text>
            </View>
          ) : null
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
  },
  form: {
    paddingHorizontal: 20,
    paddingTop: 16,
    gap: 10,
  },
  row: {
    flexDirection: "row",
    gap: 10,
  },
  input: {
    minHeight: 46,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#27313b",
    backgroundColor: "#161d24",
    paddingHorizontal: 14,
    color: "#f8fbff",
    fontSize: 15,
  },
  inputHalf: {
    flex: 1,
  },
  searchButton: {
    minHeight: 48,
    borderRadius: 8,
    backgroundColor: "#f5d451",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: 4,
  },
  searchButtonText: {
    color: "#101418",
    fontSize: 16,
    fontWeight: "800",
  },
  messageBox: {
    marginHorizontal: 20,
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    backgroundColor: "#2a1c1c",
  },
  messageText: {
    color: "#f3b7b7",
    fontSize: 13,
  },
  gridContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
    gap: 12,
  },
  gridRow: {
    justifyContent: "space-between",
    marginBottom: 12,
  },
  emptyBox: {
    alignItems: "center",
    justifyContent: "center",
    paddingTop: 40,
    gap: 8,
  },
  emptyText: {
    color: "#5b6673",
    fontSize: 14,
  },
});
